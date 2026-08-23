#!/usr/bin/env python3
"""Live 全量验证 — 用数学、英语、物理 3 份 PDF 跑完整管线（可证伪验收工具）。

用法:
  python run_live_validation.py                    # 全量验证（mock 冒烟 + live，默认无 OCR → native_only）
  python run_live_validation.py --with-ocr         # live 使用真实 PP-StructureV3（mode=live_pp）
  python run_live_validation.py --mock-only        # 仅 mock 冒烟（mode=native_mock_pp）
  python run_live_validation.py --live-only        # 仅 live（无 OCR → native_only）
  python run_live_validation.py --runs N           # live 重复次数（默认 2）
  python run_live_validation.py --run-timeout 1800 # 单次 run 超时秒数（默认 1800）

Mode 定义（report["mode"]）:
  live_pp         真实 PP-StructureV3 + 真实 LLM（Task 2.5 唯一允许 PASS 的模式）
  native_mock_pp  mock PP（native 副本）+ LLM（仅 CI/调试冒烟，overall 必 FAIL）
  native_only     无真实第二源 + 真实 LLM（冒烟，overall 必 FAIL）

overall=PASS 只允许 mode=live_pp 且全部质量阈值通过时出现。
Live 验证禁止调用 build_mock_ppsv3_doc() 作为第二源（该函数仅用于 mock 冒烟/单测）。

验收证明链：真实输入 → 可审计产物 → 可复算指标 → 通过阈值（不是 status=succeeded）。
"""

import argparse
import asyncio
import collections
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

# 从 backend/.env 加载配置
_backend_env = ROOT / "backend" / ".env"
if _backend_env.exists():
    for line in _backend_env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

from app.ai.gateway import LLMGateway
from app.ai.providers import HTTPLLMProvider, MockLLMProvider
from app.domains.document.simple_pipeline import run_simple_pipeline as run_pipeline
from paper_structure import load_manifest, validate_paper_structure

# ── 测试 PDF ──────────────────────────────────────────────
PDF_DIR = ROOT / "test" / "pdf"
GOLDEN_DIR = ROOT / "test" / "annotations" / "golden"
SUBJECTS = {
    "math": {
        "filename": "2026北京朝阳高一（上）期末数学（教师版）.pdf",
        "golden": GOLDEN_DIR / "math_real_golden.json",
    },
    "english": {
        "filename": "2026北京朝阳高一（上）期末英语（教师版）.pdf",
        "golden": GOLDEN_DIR / "english_2026_real_golden.json",
    },
    "physics": {
        "filename": "2026北京朝阳高一（上）期末物理（教师版）.pdf",
        "golden": GOLDEN_DIR / "physics_2026_real_golden.json",
    },
    "chemistry": {
        "filename": "2026北京八十中高一（上）期末化学（教师版）.pdf",
        "golden": None,
    },
    "biology": {
        "filename": "2026北京大兴高一（上）期末生物（教师版）.pdf",
        "golden": None,
    },
    "chinese": {
        "filename": "2026北京朝阳高一（上）期末语文（教师版）.pdf",
        "golden": None,
    },
}

OUTPUT_DIR = ROOT / "test" / "results" / "live_validation"

# 每科答案为空占比上限（Step 2 门禁：answer_empty 不高于 5%，原始总数口径）
MAX_ANSWER_EMPTY_RATIO = 0.05

# golden 必须存在的 8 项指标
GOLDEN_FIELDS = [
    "question_number", "question_type", "answer",
    "stem_line_ids", "options_line_ids", "answer_line_ids",
    "stem_content", "options_content",
]


# ── MockLLM 响应 ──────────────────────────────────────────
def _build_mock_response(num_lines: int) -> str:
    """构建最小合法的 LLM 标注响应（用于 mock 冒烟）。

    返回1道假题，让管线走完全流程（annotation → anchor → slice → answer → quality）。
    仅用于机械流程冒烟，不证明任何解析质量。
    """
    first_line = "P1L001" if num_lines > 0 else "P1L001"
    second_line = "P1L002" if num_lines > 1 else "P1L001"
    third_line = "P1L003" if num_lines > 2 else "P1L001"
    return json.dumps({
        "filename": "mock",
        "subject": "unknown",
        "questions": [{
            "question_number": "1",
            "question_type": "single_choice",
            "stem_line_ids": [first_line],
            "options_line_ids": {"A": [second_line], "B": [third_line]},
            "answer": "A",
            "difficulty": "medium",
            "score": 5,
            "knowledge_points": [],
        }],
        "metadata_confidence": 0.5,
        "warnings": [],
    })


# ── Gateway 构建 ──────────────────────────────────────────
def build_mock_gateway(num_lines: int) -> LLMGateway:
    """构建 mock gateway（仅用于 mock 冒烟）。"""
    return LLMGateway(mode="live", providers=[
        MockLLMProvider(response=_build_mock_response(num_lines))
    ])


def build_live_gateway() -> LLMGateway | None:
    """构建 live gateway（使用 backend/.env 中的 API key）。

    与 backend/app/ai/gateway.py 保持同步：
    - mimo-v2.5-pro 时间段切换（9-12, 14-18 优先）
    - deepseek 兜底
    """
    from app.core.config import settings
    from app.ai.gateway import _is_mimo_window

    providers = []

    # deepseek provider
    deepseek_provider = None
    if settings.deepseek_api_key and settings.deepseek_base_url and settings.deepseek_model:
        deepseek_provider = HTTPLLMProvider(
            name="deepseek",
            base_url=settings.deepseek_base_url,
            api_key=settings.deepseek_api_key,
            model=settings.deepseek_model,
            timeout_seconds=300,
        )

    # mimo provider (mimo-v2.5-pro)
    mimo_provider = None
    if settings.mimo_api_key and settings.mimo_base_url and settings.mimo_model:
        mimo_provider = HTTPLLMProvider(
            name="mimo",
            base_url=settings.mimo_base_url,
            api_key=settings.mimo_api_key,
            model=settings.mimo_model,
            timeout_seconds=300,
            response_format={"type": "json_object"},
            max_completion_tokens=131072,
        )

    # 时间段切换
    if _is_mimo_window():
        if mimo_provider:
            providers.append(mimo_provider)
        if deepseek_provider:
            providers.append(deepseek_provider)
    else:
        if deepseek_provider:
            providers.append(deepseek_provider)
        if mimo_provider:
            providers.append(mimo_provider)

    if not providers:
        return None
    return LLMGateway(mode="live", providers=providers)


# ── 复现性检查 ────────────────────────────────────────────
_REPRO_TYPE_MAP = {
    # 与 line_annotator._QUESTION_TYPE_CANONICAL 保持同步
    "experiment": "short_answer",
    "reading_expression": "short_answer",  # 英语阅读表达
    "实验题": "short_answer",
    "实验": "short_answer",
    "实验探究": "short_answer",
    "探究题": "short_answer",
    "简答题": "short_answer",
    "解答题": "short_answer",
    "计算题": "short_answer",
    "word_fill": "fill_in",
    "vocabulary_fill": "fill_in",
    "词汇填空": "fill_in",
    "选词填空": "fill_in",
    "选择题": "single_choice",
    "单选": "single_choice",
    "单选题": "single_choice",
    "单项选择": "single_choice",
    "单项选择题": "single_choice",
    "多选": "multiple_choice",
    "多选题": "multiple_choice",
    "多项选择": "multiple_choice",
    "判断题": "true_false",
    "cloze": "single_choice",  # 完形填空：每个空格本质上是单选
    "reading": "single_choice",  # 阅读理解
    "seven_to_five": "single_choice",  # 七选五
    "grammar_fill": "fill_in",  # 语法填空
}


def _repro_type(qtype: str | None) -> str:
    """复现性比较前把 LLM 题型变体归一化。"""
    return _REPRO_TYPE_MAP.get(qtype or "", qtype or "")


def check_reproducibility(result_a: dict, result_b: dict) -> list[str]:
    """比较两次运行结果，返回差异列表。

    注意：比较 question_number/type/answer/stem_line_ids/answer_line_ids，
    options/explanation_line_ids/内容不参与本检查。
    - 题型先做 canonical 归一化（experiment→short_answer 等）。
    - 答案和行号做严格比较（不做容差，等 temperature=0.0 验证后再决定）。
    """

    def _norm(s) -> str:
        s = s or ""
        # Normalize numbered answer prefixes for reproducibility.
        s = re.sub(r"(?<!\d)\d{1,3}\s*[.\u3001\uff0e]\s*", " ", s)
        s = re.sub(r"[\uFF08(]\s*\d{1,3}\s*[\uFF09)]\s*", " ", s)
        # 全角括号→半角
        s = s.replace("（", "(").replace("）", ")")
        # 移除分值标注（如 "(3分)"、"……8分"）
        s = re.sub(r"\(\d+分\)", "", s)
        s = re.sub(r"……\d+分", "", s)
        s = re.sub(r"…\d+分", "", s)
        # 移除可选评分提示（如 "（0.43~0.46均可）"）
        s = re.sub(r"\(0\.\d+~0\.\d+均可\)", "", s)
        # 标点归一化：；、，→ 空格（枚举分隔符可互换）
        s = s.replace("；", " ").replace("、", " ").replace("，", " ")
        return re.sub(r"\s+", "", s)

    errors: list[str] = []
    qs_a = {str(q["question_number"]): q for q in result_a.get("questions", []) if q.get("question_number") is not None}
    qs_b = {str(q["question_number"]): q for q in result_b.get("questions", []) if q.get("question_number") is not None}

    if set(qs_a.keys()) != set(qs_b.keys()):
        only_a = set(qs_a.keys()) - set(qs_b.keys())
        only_b = set(qs_b.keys()) - set(qs_a.keys())
        errors.append(f"question_numbers differ: only_in_a={only_a}, only_in_b={only_b}")
        return errors

    for qnum in sorted(qs_a.keys()):
        qa, qb = qs_a[qnum], qs_b[qnum]
        type_a = _repro_type(qa.get("question_type"))
        type_b = _repro_type(qb.get("question_type"))
        if type_a != type_b:
            errors.append(f"Q{qnum} type: {qa.get('question_type')} vs {qb.get('question_type')}")
        if bool(qa.get("is_composite")) != bool(qb.get("is_composite")):
            errors.append(
                f"Q{qnum} is_composite: {qa.get('is_composite')} vs {qb.get('is_composite')}"
            )
        if qa.get("is_composite"):
            # Composite reproducibility is defined by the canonical sub-question
            # contract, not by LLM top-level answer/stem boundary formatting.
            subs_a = [
                (s.get("qno"), _norm(s.get("answer")))
                for s in qa.get("sub_questions") or []
            ]
            subs_b = [
                (s.get("qno"), _norm(s.get("answer")))
                for s in qb.get("sub_questions") or []
            ]
            if subs_a != subs_b:
                errors.append(
                    f"Q{qnum} sub_questions: {subs_a} vs {subs_b}"
                )
            if sorted(qa.get("answer_line_ids", [])) != sorted(qb.get("answer_line_ids", [])):
                errors.append(
                    f"Q{qnum} answer_line_ids: {qa.get('answer_line_ids')} "
                    f"vs {qb.get('answer_line_ids')}"
                )
        else:
            if _norm(qa.get("answer")) != _norm(qb.get("answer")):
                errors.append(f"Q{qnum} answer: {qa.get('answer')!r} vs {qb.get('answer')!r}")
            if sorted(qa.get("stem_line_ids", [])) != sorted(qb.get("stem_line_ids", [])):
                errors.append(f"Q{qnum} stem_line_ids: {qa.get('stem_line_ids')} vs {qb.get('stem_line_ids')}")
            if sorted(qa.get("answer_line_ids", [])) != sorted(qb.get("answer_line_ids", [])):
                errors.append(
                    f"Q{qnum} answer_line_ids: {qa.get('answer_line_ids')} "
                    f"vs {qb.get('answer_line_ids')}"
                )

    # 检测内部重复 line_id（sorted 比较会掩盖同一 run 内的重复）
    for label, result in [("run_a", result_a), ("run_b", result_b)]:
        for q in result.get("questions", []):
            qnum = q.get("question_number")
            stem_ids = q.get("stem_line_ids", [])
            dups = [lid for lid, cnt in collections.Counter(stem_ids).items() if cnt > 1]
            if dups:
                errors.append(f"Q{qnum} {label} stem_line_ids has duplicates: {dups}")

    return errors

def build_mock_ppsv3_doc(native_doc):
    """从 native L1 构建 mock PP L1（复制行，改 source 为 ppsv3）。

    警告：该函数产生的"第二源"是 native 副本，双源仲裁必然零冲突，
    只用于 mock 冒烟与单元测试，**禁止**作为 Task 2.5 live 验证的真实第二源。
    """
    from app.domains.document.schemas_l1 import L1Document, L1Line, L1Page
    pages = [L1Page(page_no=p.page_no, lines=[], images=list(p.images)) for p in native_doc.pages]
    lines = []
    for line in native_doc.lines:
        lines.append(L1Line(
            line_id=line.line_id, page_no=line.page_no,
            line_no_in_page=line.line_no_in_page, order=line.order,
            text=line.text, block_type=line.block_type,
            source="ppsv3", continuation=line.continuation,
            bbox=line.bbox,
        ))
    return L1Document(
        filename=native_doc.filename, pages=pages, lines=lines,
        source="ppsv3", total_pages=native_doc.total_pages,
        text_coverage=native_doc.text_coverage,
    )


# ── 单次运行 ──────────────────────────────────────────────
async def run_one(
    pdf_path: Path | None,
    gateway: LLMGateway,
    label: str,
    *,
    native_doc=None,
    ppsv3_doc=None,
    run_timeout: float = 1800.0,
    progress_callback=None,
) -> dict:
    """运行一次管线，返回 result.to_dict()。

    当传入 native_doc/ppsv3_doc 时，跳过 PDF 提取/OCR。
    run_timeout 为单次 run 超时；超时或异常时返回 status=failed 的 run JSON，
    避免脚本无限等待。progress_callback 为可选异步回调；未传入时打印 stage 进度。
    """
    t0 = time.perf_counter()
    kwargs: dict = {"gateway": gateway}
    if pdf_path is not None:
        kwargs["pdf_path"] = pdf_path
        kwargs["filename"] = pdf_path.name  # 学科路由需要 filename
    if native_doc is not None:
        kwargs["native_doc"] = native_doc
    if ppsv3_doc is not None:
        kwargs["ppsv3_doc"] = ppsv3_doc

    if progress_callback is None:
        async def _default_progress(stage: str, progress: float) -> None:
            print(
                f"  [{label}] {time.strftime('%H:%M:%S')} "
                f"stage={stage} progress={progress:.0%}",
                flush=True,
            )
        progress_callback = _default_progress
    kwargs["progress_callback"] = progress_callback

    try:
        result = await asyncio.wait_for(
            run_pipeline(**kwargs),
            timeout=run_timeout,
        )
    except asyncio.TimeoutError:
        elapsed = time.perf_counter() - t0
        return _failed_run_result(
            label,
            f"run timed out after {run_timeout:.0f}s",
            elapsed,
        )
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        return _failed_run_result(
            label,
            f"run failed: {type(exc).__name__}: {exc}",
            elapsed,
        )

    elapsed = time.perf_counter() - t0
    d = result.to_dict()
    d["_elapsed_s"] = round(elapsed, 1)
    d["_label"] = label
    return d


def _failed_run_result(label: str, error: str, elapsed_s: float) -> dict:
    """构造超时/异常 run 的统一失败产物。"""
    return {
        "status": "failed",
        "stages": [{"name": "run_failed", "error": error}],
        "stage_errors": [{"stage": "run_failed", "error": error}],
        "total_time_ms": int(elapsed_s * 1000),
        "errors": [error],
        "question_count": 0,
        "images": [],
        "question_images": [],
        "questions": [],
        "_elapsed_s": round(elapsed_s, 1),
        "_label": label,
    }


# ── 质量统计 ──────────────────────────────────────────────
def compute_quality_stats(result: dict) -> dict:
    """从 run result 计算每科质量指标。

    answer_empty_ratio 使用原始总数口径（Step 2 门禁：answer_empty 不高于 5%），
    不区分题型（解答题空答案同样计入）。
    """
    qs = result.get("questions", [])
    answer_matched = sum(1 for q in qs if (q.get("answer") or "").strip())
    answer_empty_total = sum(1 for q in qs if not (q.get("answer") or "").strip())
    with_issues = sum(1 for q in qs if q.get("issues"))
    total_issues = sum(len(q.get("issues") or []) for q in qs)
    # blocked：优先 quality_gate stage 输出（WP3 落地后），否则从 issues 计算
    blocked = None
    high_conf = None
    for st in result.get("stages", []):
        if st.get("name") == "quality_gate":
            high_conf = st.get("high_confidence")
            blocked = st.get("blocked")
    if blocked is None:
        blocked = sum(1 for q in qs if any("禁止自动发布" in i for i in (q.get("issues") or [])))
    return {
        "question_count": len(qs),
        "answer_matched": answer_matched,
        "answer_empty": answer_empty_total,
        "answer_empty_ratio": round(answer_empty_total / len(qs), 4) if qs else 1.0,
        "high_conf": high_conf,
        "blocked": blocked,
        "questions_with_issues": with_issues,
        "total_issues": total_issues,
        # question_images（Step 2 门禁项：有图片的文档关联数必须 > 0）
        # 只统计有 bbox 的真实内容图；PP 每页的 layout/ocr 诊断图无 bbox，不能作为题图门禁证据。
        "images_count": sum(
            1 for img in (result.get("images", []) or [])
            if img.get("bbox")
        ),
        "question_images_count": len(result.get("question_images", []) or []),
        "question_images_placements": sorted({
            (qi.get("placement") if isinstance(qi, dict) else "?")
            for qi in (result.get("question_images", []) or [])
        }),
        # 纸张结构信息
        "composite_count": sum(1 for q in qs if q.get("is_composite")),
        "sub_questions_count": sum(len(q.get("sub_questions") or []) for q in qs),
    }


def ppsv3_l1_source(result: dict) -> str:
    """返回 ppsv3_l1 stage 的来源标签：real_ocr / pre_computed / not_run / failed。"""
    for st in result.get("stages", []):
        if st.get("name") == "ppsv3_l1":
            if st.get("error"):
                return "failed"
            if st.get("note") == "pre-computed":
                return "pre_computed"
            return "real_ocr"
    return "not_run"


# ── 报告生成 ──────────────────────────────────────────────
def _ok(msg: str) -> str:
    return f"  [OK] {msg}"


def _fail(msg: str) -> str:
    return f"  [FAIL] {msg}"


def evaluate_golden_for_subject(result: dict, golden_path: Path):
    """对单科跑 golden 8 项指标；golden 文件缺失返回 None。"""
    if golden_path is None or not golden_path.exists():
        return None
    golden = json.loads(golden_path.read_text(encoding="utf-8"))
    sys.path.insert(0, str(ROOT / "test" / "scripts"))
    from run_phase1_eval import evaluate_accuracy
    acc = evaluate_accuracy(result.get("questions", []), golden)
    return {f: {"correct": c, "total": t} for f, (c, t) in acc.items()}


def generate_report(
    mode: str,
    mock_results: dict[str, dict],
    live_runs: dict[str, list[dict]],
    reproducibility: dict[str, list[str]],
    golden_accuracy: dict[str, dict | None],
    quality: dict[str, dict],
    ppsv3_sources: dict[str, str],
    ocr_attempted: bool,
    paper_structure: dict[str, list[dict]] | None = None,
) -> dict:
    """生成结构化报告；overall=PASS 只允许 mode=live_pp 且全部阈值通过。"""
    report: dict = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "mode": mode,
        "ocr_attempted": ocr_attempted,
        "mock": {},
        "live": {},
        "quality": quality,
        "ppsv3_l1_source": ppsv3_sources,
        "reproducibility": {},
        "golden_accuracy": {},
        "paper_structure": {},
        "overall": "PASS",
        "failures": [],
    }

    # mock 结果（冒烟，不参与 overall）
    for subject, r in mock_results.items():
        report["mock"][subject] = {
            "status": r.get("status"),
            "question_count": r.get("question_count", 0),
            "errors": r.get("errors", []),
            "elapsed_s": r.get("_elapsed_s", 0),
        }

    # live 结果
    for subject, runs in live_runs.items():
        report["live"][subject] = []
        for i, r in enumerate(runs):
            report["live"][subject].append({
                "run": i + 1,
                "status": r.get("status"),
                "question_count": r.get("question_count", 0),
                "errors": r.get("errors", []),
                "elapsed_s": r.get("_elapsed_s", 0),
            })
            if r.get("status") != "succeeded":
                report["failures"].append(f"live:{subject} run={i+1} status={r.get('status')}")

    # 复现性
    for subject, diffs in reproducibility.items():
        report["reproducibility"][subject] = {
            "match": len(diffs) == 0,
            "differences": diffs,
        }
        if diffs and diffs != ["only 1 run, cannot check"]:
            report["failures"].append(f"reproducibility:{subject} {len(diffs)} differences")

    # golden 8 项指标（三科）
    for subject, acc in golden_accuracy.items():
        if acc is None:
            report["golden_accuracy"][subject] = None
            report["failures"].append(f"golden:{subject} missing golden file or metrics")
            continue
        report["golden_accuracy"][subject] = acc
        missing_fields = [f for f in GOLDEN_FIELDS if f not in acc]
        if missing_fields:
            report["failures"].append(
                f"golden:{subject} missing fields {missing_fields}"
            )

    # Paper structure gate: canonical grouping, sub-questions and shared material.
    for subject, run_infos in (paper_structure or {}).items():
        report["paper_structure"][subject] = run_infos
        for run_info in run_infos:
            if not run_info.get("valid"):
                detail = "; ".join(run_info.get("errors") or ["invalid structure"])
                report["failures"].append(
                    f"paper_structure:{subject} run={run_info.get('run')}: {detail}"
                )

    # ── overall 门禁判定 ──
    # 1. mode 必须是 live_pp
    if mode != "live_pp":
        report["failures"].append(f"mode={mode} != live_pp (Task 2.5 只接受真实 PP + 真实 LLM)")

    # 2. mock 冒烟结果必须存在（全量验证要求）
    if not mock_results:
        report["failures"].append("mock block empty: mock smoke must run and be persisted")

    # 3. ppsv3_l1 必须是真实 OCR
    for subject, src in ppsv3_sources.items():
        if src != "real_ocr":
            report["failures"].append(f"ppsv3_l1:{subject} source={src} (需要 real_ocr)")

    # 4. 质量阈值：每科 answer_empty（原始总数口径）<= 5%
    for subject, q in quality.items():
        ratio = q.get("answer_empty_ratio", 1.0)
        if ratio > MAX_ANSWER_EMPTY_RATIO:
            report["failures"].append(
                f"quality:{subject} answer_empty="
                f"{q.get('answer_empty')}/{q.get('question_count')} "
                f"({ratio:.1%}) > {MAX_ANSWER_EMPTY_RATIO:.0%}"
            )

    # 5. question_images 门禁：有图片的文档关联数必须 > 0（Step 2 门禁项）
    for subject, q in quality.items():
        img_count = q.get("images_count", 0)
        qi_count = q.get("question_images_count", 0)
        if img_count > 0 and qi_count == 0:
            report["failures"].append(
                f"question_images:{subject} images={img_count} but "
                f"question_images_count=0（有图片但无题-图关联）"
            )

    if report["failures"]:
        report["overall"] = "FAIL"

    return report


def print_report(report: dict) -> None:
    """打印人类可读报告。"""
    print(f"\n{'='*60}")
    print(f"Live Validation Report — {report['timestamp']}")
    print(f"  mode: {report['mode']}  (ocr_attempted={report.get('ocr_attempted')})")
    print(f"{'='*60}")

    print("\n--- Mock Mode (smoke only, not gating) ---")
    for subject, info in report["mock"].items():
        if info["status"] == "succeeded":
            print(_ok(f"{subject}: succeeded, {info['question_count']} questions, {info['elapsed_s']}s"))
        else:
            print(_fail(f"{subject}: {info['status']}, errors={info['errors']}"))
    if not report["mock"]:
        print(_fail("mock block is empty"))

    for subject, runs in report["live"].items():
        print(f"\n--- Live Mode ({subject}) ---")
        for run_info in runs:
            if run_info["status"] == "succeeded":
                print(_ok(f"Run {run_info['run']}: succeeded, "
                          f"{run_info['question_count']} questions, {run_info['elapsed_s']}s"))
            else:
                print(_fail(f"Run {run_info['run']}: {run_info['status']}, "
                            f"errors={run_info['errors']}"))

    print("\n--- Quality (per subject) ---")
    for subject, q in report.get("quality", {}).items():
        print(f"  {subject}: questions={q['question_count']} answer_matched={q['answer_matched']} "
              f"answer_empty={q['answer_empty']} [{q['answer_empty_ratio']:.1%}] "
              f"high_conf={q['high_conf']} blocked={q['blocked']} "
              f"questions_with_issues={q['questions_with_issues']} "
              f"question_images={q.get('question_images_count', 0)}/{q.get('images_count', 0)} "
              f"placement={q.get('question_images_placements', [])}")
    print("\n--- ppsv3_l1 source ---")
    for subject, src in report.get("ppsv3_l1_source", {}).items():
        print(f"  {subject}: {src}")

    print("\n--- Reproducibility ---")
    for subject, info in report["reproducibility"].items():
        if info["match"]:
            print(_ok(f"{subject}: match"))
        else:
            print(_fail(f"{subject}: {len(info['differences'])} differences"))
            for d in info["differences"][:5]:
                print(f"    - {d}")

    print("\n--- Paper Structure ---")
    for subject, infos in report.get("paper_structure", {}).items():
        for info in infos:
            if info.get("valid"):
                stats = info.get("stats", {})
                print(_ok(
                    f"{subject} run={info.get('run')}: "
                    f"top={stats.get('top_level_count')} "
                    f"composite={stats.get('composite_count')} "
                    f"bottom={stats.get('bottom_level_count')}"
                ))
            else:
                detail = "; ".join(info.get("errors", [])[:5])
                print(_fail(f"{subject} run={info.get('run')}: {detail}"))

    if report.get("golden_accuracy"):
        print("\n--- Golden Accuracy (per subject, 8 fields) ---")
        for subject, acc in report["golden_accuracy"].items():
            if acc is None:
                print(_fail(f"{subject}: missing golden metrics"))
                continue
            for field, stats in acc.items():
                c, t = stats["correct"], stats["total"]
                a = c / t if t else 0
                print(f"  {subject}.{field}: {c}/{t} = {a:.1%}")

    print(f"\n{'='*60}")
    if report["overall"] == "PASS":
        print(f"PASS: Live Validation (mode={report['mode']})")
    else:
        print(f"FAIL: Live Validation (mode={report['mode']})")
        for f in report["failures"]:
            print(f"  FAIL: {f}")
    print(f"{'='*60}")


# ── 主流程 ────────────────────────────────────────────────
async def main() -> int:
    parser = argparse.ArgumentParser(description="Live 全量验证（可证伪验收工具）")
    parser.add_argument("--mock-only", action="store_true", help="仅运行 mock 冒烟")
    parser.add_argument("--live-only", action="store_true", help="仅运行 live")
    parser.add_argument("--with-ocr", action="store_true", help="live 使用真实 PP-StructureV3（mode=live_pp）")
    parser.add_argument("--runs", type=int, default=2, help="live 重复次数（默认 2）")
    parser.add_argument("--run-timeout", type=float, default=1800.0,
                        help="单次 live run 超时秒数（默认 1800）")
    parser.add_argument("--subjects", type=str, default=None,
                        help="逗号分隔的科目列表（如 math,english,physics），默认全部")
    args = parser.parse_args()

    run_mock = not args.live_only
    run_live = not args.mock_only
    num_runs = max(1, args.runs)

    # 过滤科目
    subjects = SUBJECTS
    if args.subjects:
        selected = {s.strip() for s in args.subjects.split(",")}
        subjects = {k: v for k, v in SUBJECTS.items() if k in selected}
        if not subjects:
            print(f"ERROR: no valid subjects in --subjects {args.subjects}")
            print(f"Available: {', '.join(SUBJECTS.keys())}")
            return

    print(f"\n{'='*60}")
    print(f"Live Validation — mock={'on' if run_mock else 'off'}, "
          f"live={'on' if run_live else 'off'}, ocr={args.with_ocr}, runs={num_runs}")
    print(f"{'='*60}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    mock_results: dict[str, dict] = {}
    live_runs: dict[str, list[dict]] = {}
    reproducibility: dict[str, list[str]] = {}
    golden_accuracy: dict[str, dict | None] = {s: None for s in subjects}
    quality: dict[str, dict] = {}
    ppsv3_sources: dict[str, str] = {}
    paper_structure: dict[str, list[dict]] = {}

    # ── Mock 冒烟 ──
    # mock 模式：native L1 + mock PP 副本 + MockLLM；mode=native_mock_pp
    # 只验证机械流程不断裂，不参与 overall 判定
    if run_mock:
        print("\n>>> Mock Mode (smoke only) <<<")
        from app.domains.document.native_markdown import extract_l1_from_pdf

        for subject, info in subjects.items():
            pdf_path = PDF_DIR / info["filename"]
            if not pdf_path.exists():
                print(_fail(f"{subject}: PDF not found at {pdf_path}"))
                continue
            print(f"\n  [{subject}] Extracting native L1...")
            try:
                native_doc = extract_l1_from_pdf(pdf_path, filename=info["filename"])
                num_lines = len(native_doc.lines)
                print(f"    Native L1: {num_lines} lines")
            except Exception as exc:
                print(_fail(f"{subject}: native extraction failed: {exc}"))
                continue

            ppsv3_doc = build_mock_ppsv3_doc(native_doc)
            gateway = build_mock_gateway(num_lines)
            r = await run_one(None, gateway, f"mock:{subject}",
                              native_doc=native_doc, ppsv3_doc=ppsv3_doc,
                              run_timeout=args.run_timeout)
            mock_results[subject] = r
            out_path = OUTPUT_DIR / f"mock_{subject}.json"
            out_path.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
            print(_ok(f"{subject}: {r.get('status')}, {r.get('question_count')} questions, "
                      f"{r['_elapsed_s']}s -> {out_path.name}"))

    # ── Live 模式 ──
    # 无 OCR（默认）：native-only 单源，mode=native_only，禁止 mock PP 充当第二源
    # --with-ocr：真实 PP-StructureV3，mode=live_pp（Task 2.5 唯一可 PASS 模式）
    if run_live:
        print("\n>>> Live Mode <<<")
        gateway = build_live_gateway()
        if gateway is None:
            print(_fail("No live LLM providers configured in backend/.env"))
            return 1

        mode = "live_pp" if args.with_ocr else "native_only"
        from app.domains.document.native_markdown import extract_l1_from_pdf

        for subject, info in subjects.items():
            pdf_path = PDF_DIR / info["filename"]
            if not pdf_path.exists():
                print(_fail(f"{subject}: PDF not found at {pdf_path}"))
                continue

            live_runs[subject] = []
            for run_idx in range(num_runs):
                print(f"  [{subject}] Run {run_idx + 1}/{num_runs} "
                      f"(mode={mode})...")
                if args.with_ocr:
                    # 真实 OCR：让 pipeline 内部跑 native 提取 + OCR 链
                    r = await run_one(pdf_path, gateway, f"live:{subject}:run{run_idx+1}",
                                      run_timeout=args.run_timeout)
                else:
                    # native-only：显式传 native_doc，pipeline 不尝试 OCR
                    try:
                        native_doc = extract_l1_from_pdf(pdf_path, filename=info["filename"])
                        print(f"    Native L1: {len(native_doc.lines)} lines")
                    except Exception as exc:
                        print(_fail(f"{subject}: native extraction failed: {exc}"))
                        break
                    r = await run_one(None, gateway, f"live:{subject}:run{run_idx+1}",
                                      native_doc=native_doc,
                                      run_timeout=args.run_timeout)

                live_runs[subject].append(r)
                out_path = OUTPUT_DIR / f"{subject}_run{run_idx+1}.json"
                out_path.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
                status = r.get("status", "unknown")
                qc = r.get("question_count", 0)
                if status == "succeeded":
                    print(_ok(f"Run {run_idx+1}: succeeded, {qc} questions, {r['_elapsed_s']}s"))
                else:
                    print(_fail(f"Run {run_idx+1}: {status}, errors={r.get('errors', [])}"))

            if not live_runs[subject]:
                continue
            # 质量统计（取 run1）
            quality[subject] = compute_quality_stats(live_runs[subject][0])
            ppsv3_sources[subject] = ppsv3_l1_source(live_runs[subject][0])
            golden_accuracy[subject] = evaluate_golden_for_subject(
                live_runs[subject][0], subjects[subject]["golden"])

            if len(live_runs[subject]) >= 2:
                diffs = check_reproducibility(live_runs[subject][0], live_runs[subject][1])
                reproducibility[subject] = diffs
                if not diffs:
                    print(_ok(f"{subject}: reproducible ({len(live_runs[subject][0].get('questions', []))} questions)"))
                else:
                    print(_fail(f"{subject}: {len(diffs)} differences"))
                    for d in diffs[:5]:
                        print(f"    - {d}")
            else:
                reproducibility[subject] = ["only 1 run, cannot check"]

            # Canonical paper structure must hold for every live run.
            structure_runs = []
            manifest = load_manifest(subject)
            if manifest is not None:
                for run_idx, run_result in enumerate(live_runs[subject], 1):
                    info = validate_paper_structure(run_result, manifest)
                    info["run"] = run_idx
                    structure_runs.append(info)
                    if not info["valid"]:
                        detail = "; ".join(info["errors"][:5])
                        print(_fail(f"paper_structure:{subject} run={run_idx}: {detail}"))
                if structure_runs:
                    paper_structure[subject] = structure_runs

    if not live_runs:
        # 仅 mock 模式：mode=native_mock_pp
        mode = "native_mock_pp"
        ocr_attempted = False
    else:
        # mode 按实际 ppsv3_l1 来源判定：只有全部科目都是真实 OCR 才算 live_pp
        if (args.with_ocr and ppsv3_sources
                and all(src == "real_ocr" for src in ppsv3_sources.values())):
            mode = "live_pp"
        else:
            mode = "native_only"
        ocr_attempted = args.with_ocr

    report = generate_report(
        mode=mode,
        mock_results=mock_results,
        live_runs=live_runs,
        reproducibility=reproducibility,
        golden_accuracy=golden_accuracy,
        quality=quality,
        ppsv3_sources=ppsv3_sources,
        ocr_attempted=ocr_attempted,
        paper_structure=paper_structure,
    )

    report_path = OUTPUT_DIR / "report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print_report(report)
    print(f"\nFull report saved to: {report_path}")

    return 0 if report["overall"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

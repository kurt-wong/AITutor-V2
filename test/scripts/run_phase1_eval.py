#!/usr/bin/env python3
"""Phase 1 Golden Set eval — 基于冻结 PP JSONL 的确定性验收。

用法:
  python run_phase1_eval.py                # 默认模式（冻结 PP + MockLLM，CI 回归）
  python run_phase1_eval.py --live         # 默认模式 + 真实 LLM（冻结 PP，行号 100%）
  python run_phase1_eval.py --live-pp      # 真实 PP + 真实 LLM（端到端 smoke，内容校验为主）

验收逻辑:
  - 默认模式：冻结 PP JSONL → 确定性 L1 → golden 行号 100% exact
  - --live：冻结 PP + 真实 LLM，验证 LLM 标注质量（行号仍 100% exact）
  - --live-pp：真实 PP smoke，内容 + pipeline health 为主，不宣称行号 100%
"""

import asyncio
import json
import os
import re
import unicodedata
import sys
from collections import Counter
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
from app.ai.providers import MockLLMProvider
from app.domains.document.pipeline import run_pipeline

PDF_PATH = ROOT / "test" / "pdf" / "2026北京朝阳高一（上）期末数学（教师版）.pdf"
GOLDEN_PATH = ROOT / "test" / "annotations" / "golden" / "math_real_golden.json"
FIXTURE_PATH = ROOT / "test" / "fixtures" / "l1_snapshot_math_real_ppsv3_postprocessed.json"
NATIVE_FIXTURE_PATH = ROOT / "test" / "fixtures" / "l1_snapshot_math_real.json"

_Q_PREFIX_RE = re.compile(r"^[（(]\s*\d{1,3}\s*[）)]\s*")
_INLINE_OPTION_LABEL_RE = re.compile(r"(?:^|[^A-H])([A-H])[.、．]")

# Golden 比较前做语义级归一化：LaTeX、空格、分值后缀、常见符号差异
# 不应把格式差异误判为答案错误。此函数保持纯文本转换，不改变原始字段。
_LATEX_FRAC_RE = re.compile(
    r"\\(?:frac|dfrac)\{((?:[^{}]|\{[^{}]*\})*)\}\{((?:[^{}]|\{[^{}]*\})*)\}"
)
_LATEX_SQRT_RE = re.compile(r"\\sqrt\{([^{}]+)\}")
_LATEX_REMOVE_CMDS = (
    "left", "right", "big", "Big", "bigg", "Bigg", "text", "mathbf", "mathbb",
)
_LATEX_SYMBOL_MAP = {
    r"\bigcup": "U",
    r"\cup": "U",
    r"\cap": "n",
    r"\infty": "inf",
    r"\in": "in",
    r"\geqslant": ">=",
    r"\geq": ">=",
    r"\leqslant": "<=",
    r"\leq": "<=",
    r"\neq": "!=",
    r"\times": "*",
    r"\cdot": "*",
    r"\pi": "pi",
    r"\cos": "cos",
    r"\sin": "sin",
    r"\tan": "tan",
    r"\log": "log",
    r"\lg": "lg",
    r"\ln": "ln",
    r"\{": "{",
    r"\}": "}",
    r"\mid": "|",
}
_SCORE_PAREN_RE = re.compile(r"[（(][^）)]*\d+\s*分[^）)]*[）)]\s*$")
_SCORE_BARE_RE = re.compile(r"(?:…+\s*)?\d+\s*分\s*$")


def normalize_answer_text(text: str | None) -> str:
    """归一化答案文本用于 golden 比较。

    - 忽略全半角、引号样式、题号前缀、OCR 转义和常见分隔符噪音
    - 去除 LaTeX 包裹符与常见命令
    - 转换常见数学符号为可比较文本
    - 剥离分值后缀（B (2分) → B）
    - 去除全部空白
    """
    if not text:
        return ""
    s = unicodedata.normalize("NFKC", str(text)).strip()
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("$", "")
    # 简单分数优先转换，支持 \frac{a}{b} / \dfrac{a}{b}
    for _ in range(3):
        s = _LATEX_FRAC_RE.sub(r"\1/\2", s)
    s = _LATEX_SQRT_RE.sub(r"sqrt(\1)", s)
    for cmd in _LATEX_REMOVE_CMDS:
        s = re.sub(rf"\\{cmd}\b", "", s)
    for token, replacement in _LATEX_SYMBOL_MAP.items():
        s = s.replace(token, replacement)
    s = _SCORE_PAREN_RE.sub("", s)
    s = _SCORE_BARE_RE.sub("", s)
    # 去掉答案开头的题号前缀，如 44. / 45.
    s = re.sub(r"^(?:\d{1,3}\s*[.、．:：]\s*)+", "", s)
    # 统一答案中的分隔符噪音：/、##、顿号、逗号、分号、竖线
    s = re.sub(r"(?:\s*##\s*|\s*/\s*|\s*、\s*|\s*[，,;；|]\s*)+", "/", s)
    s = re.sub(r"\s+", "", s)
    return s.strip("。．.;；;，,?!?！:：\"'")

# Phase 1 验收阈值（默认模式：冻结 PP + MockLLM，行号 100% exact）
THRESHOLDS_EXACT = {
    "question_number": 1.0, "question_type": 1.0, "answer": 1.0,
    "stem_line_ids": 1.0, "options_line_ids": 1.0, "answer_line_ids": 1.0,
    "stem_content": 1.0, "options_content": 1.0,
}

# live 阈值（冻结 PP + 真实 LLM，corrected anchor 确定性校正后行号 100%）
THRESHOLDS_LIVE = {
    "question_number": 1.0, "question_type": 1.0, "answer": 1.0,
    "stem_line_ids": 1.0, "options_line_ids": 1.0, "answer_line_ids": 1.0,
    "stem_content": 1.0, "options_content": 1.0,
}

# live-pp smoke 阈值（真实 PP + 真实 LLM，golden 指标 + line_ids）
THRESHOLDS_SMOKE = {
    "question_number": 1.0, "question_type": 1.0, "answer": 1.0,
    "stem_line_ids": 1.0, "options_line_ids": 1.0, "answer_line_ids": 1.0,
    "stem_content": 1.0, "options_content": 1.0,
}

# 全卷验收阈值（live-pp smoke 模式，防止 golden 过但全卷变差）
THRESHOLDS_FULL卷 = {
    "min_answer_matched": 16,    # 全卷答案匹配数 ≥ 16/21
    "max_blocked": 7,            # 全卷 blocked 数 ≤ 7/21
    "min_quality_high": 14,      # 全卷高质量题数 ≥ 14/21
    "max_missing_anchors": 10,   # 全卷 missing 锚点 ≤ 10
}


def _compare_options_line_ids(actual: dict, expected: dict) -> bool:
    """比较两个 options_line_ids 字典的每个选项的行号列表。"""
    if set(actual.keys()) != set(expected.keys()):
        return False
    for key in actual:
        a_ids = sorted(actual[key])
        e_ids = sorted(expected[key])
        if a_ids != e_ids:
            return False
    return True


def _compare_sub_questions(actual_question: dict, expected_question: dict) -> bool:
    """比较综合题的子题 qno 与每个子题 options_line_ids。"""
    expected_subs = expected_question.get("sub_questions") or []
    actual_subs = actual_question.get("sub_questions") or []
    if len(expected_subs) != len(actual_subs):
        return False

    actual_by_qno: dict[str, dict] = {}
    for sub in actual_subs:
        qno = str(sub.get("qno") or sub.get("question_number") or "")
        actual_by_qno[qno] = sub

    for expected in expected_subs:
        qno = str(expected.get("qno") or expected.get("question_number") or "")
        actual = actual_by_qno.get(qno)
        if actual is None:
            return False
        if not _compare_options_line_ids(
            actual.get("options_line_ids") or {},
            expected.get("options_line_ids") or {},
        ):
            return False
    return True


def _option_completeness_correct(question: dict) -> bool:
    """检查选项数量对应的文本完整性：空选项或一行内嵌多个选项视为不完整。"""
    options = question.get("options") or []
    if not options:
        return True
    for option in options:
        text = str(option.get("text") or "").strip()
        if not text:
            return False
        if len(_INLINE_OPTION_LABEL_RE.findall(text)) > 1:
            return False
    return True

def _extract_corrected_line_ids(question: dict) -> dict:
    """从 corrected_anchors 提取确定性校正后的行号。

    anchor corrector 使用文本匹配/题号匹配做确定性校正，
    不直接采信 LLM 原始行号，因此 corrected_line_ids 是
    评估 line ID 准确率的正确比较对象。

    answer_line_ids 不经过 anchor corrector，由 answer_matcher
    确定性设置（答案表匹配/内联答案匹配），直接从 question dict 取。

    Returns:
        {
            "stem_line_ids": [...],
            "options_line_ids": {"A": [...], "B": [...], ...},
            "answer_line_ids": [...],
        }
    """
    corrected = {
        "stem_line_ids": [],
        "options_line_ids": {},
        "answer_line_ids": question.get("answer_line_ids", []),
    }
    for ca in question.get("corrected_anchors", []):
        field = ca.get("field", "")
        corrected_ids = ca.get("corrected_line_ids", [])
        if field == "stem":
            corrected["stem_line_ids"] = corrected_ids
        elif field.startswith("option_"):
            # "option_A" → "A"
            label = field.split("_", 1)[1]
            corrected["options_line_ids"][label] = corrected_ids
    return corrected


def load_golden():
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


def load_fixture():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def load_native_fixture():
    """加载真实 native fixture（PyMuPDF 提取，有真实 bbox）。"""
    return json.loads(NATIVE_FIXTURE_PATH.read_text(encoding="utf-8"))


def build_native_doc_from_fixture(fixture):
    """从真实 native fixture 构建 L1Document（保留真实 bbox）。"""
    from app.domains.document.schemas_l1 import L1Document, L1Line, L1Page
    pages = [L1Page(page_no=p["page_no"], lines=[], images=[]) for p in fixture["pages"]]
    lines = []
    for l in fixture["lines"]:
        bbox = l.get("bbox")  # 真实 bbox，可能为 None
        lines.append(L1Line(
            line_id=l["line_id"], page_no=l["page_no"],
            line_no_in_page=l["line_no_in_page"], order=l["order"],
            text=l["text"], block_type=l["block_type"],
            source="native", continuation=l.get("continuation", False),
            bbox=bbox,
        ))
    return L1Document(
        filename=fixture["filename"], pages=pages, lines=lines,
        source="native", total_pages=len(pages), text_coverage=1.0,
    )


def build_mock_response(golden):
    """构建 MockLLM 响应：从 golden 复制行号标注（用于 mock 模式）。"""
    qs = []
    for q in golden["questions"]:
        qs.append({
            "question_number": q["question_number"],
            "question_type": q["question_type"],
            "section_id": q.get("section_id"),
            "stem_line_ids": q["stem_line_ids"],
            "options_line_ids": q.get("options_line_ids", {}),
            "answer": q.get("answer", ""),
            "difficulty": q.get("difficulty"),
            "score": q.get("score"),
            "knowledge_points": q.get("knowledge_points", []),
        })
    return json.dumps({
        "filename": golden["filename"], "subject": "math",
        "questions": qs, "metadata_confidence": 0.9, "warnings": [],
    })


def build_ppsv3_doc_from_fixture(fixture):
    """从冻结 fixture 构建 PP L1Document（保留 fixture 中的真实 bbox）。"""
    from app.domains.document.schemas_l1 import L1Document, L1Line, L1Page
    pages = [L1Page(page_no=p["page_no"], lines=[], images=[]) for p in fixture["pages"]]
    lines = []
    for l in fixture["lines"]:
        bbox = l.get("bbox")  # 使用 fixture 中的真实 bbox（可能为 None）
        lines.append(L1Line(
            line_id=l["line_id"], page_no=l["page_no"],
            line_no_in_page=l["line_no_in_page"], order=l["order"],
            text=l["text"], block_type=l["block_type"],
            source="ppsv3", continuation=l.get("continuation", False),
            bbox=bbox,
        ))
    return L1Document(
        filename=fixture["filename"], pages=pages, lines=lines,
        source="ppsv3", total_pages=len(pages), text_coverage=1.0,
    )


def build_mock_native_doc_from_fixture(fixture):
    """从冻结 fixture 构建 mock native L1Document。

    与 PP fixture 共享 line_id 和 bbox（保证 merge 正确配对），
    部分行引入文本差异，让仲裁器真正做冲突决策（exercise arbitration logic）。
    """
    import hashlib
    from app.domains.document.schemas_l1 import L1Document, L1Line, L1Page
    pages = [L1Page(page_no=p["page_no"], lines=[], images=[]) for p in fixture["pages"]]
    lines = []
    for i, l in enumerate(fixture["lines"]):
        y_start = i * 20
        bbox = {"x1": 50, "y1": float(y_start), "x2": 550, "y2": float(y_start + 18)}
        text = l["text"]
        # 对 ~30% 的行引入文本差异（模拟 native 提取偏差）
        # 用确定性哈希选择，不依赖 random
        h = int(hashlib.md5(l["line_id"].encode()).hexdigest()[:8], 16)
        if h % 10 < 3 and len(text) > 5:
            # 在行尾加一个空格（模拟 native 提取的微小差异）
            text = text + " "
        lines.append(L1Line(
            line_id=l["line_id"], page_no=l["page_no"],
            line_no_in_page=l["line_no_in_page"], order=l["order"],
            text=text, block_type=l["block_type"],
            source="native", continuation=l.get("continuation", False),
            bbox=bbox,
        ))
    return L1Document(
        filename=fixture["filename"], pages=pages, lines=lines,
        source="native", total_pages=len(pages), text_coverage=1.0,
    )


def evaluate_accuracy(result_questions, golden):
    """字段级准确率评估。"""
    gmap = {q["question_number"]: q for q in golden["questions"]}
    fields = {
        "question_number": [0, 0], "question_type": [0, 0],
        "answer": [0, 0], "stem_line_ids": [0, 0],
        "options_line_ids": [0, 0], "answer_line_ids": [0, 0],
        "stem_content": [0, 0], "options_content": [0, 0],
        "sub_questions_count": [0, 0],
        "sub_question_options_line_ids": [0, 0],
        "option_completeness": [0, 0],
    }
    for rq in result_questions:
        gq = gmap.get(rq.get("question_number", ""))
        if not gq:
            continue

        # 提取 corrected line IDs（anchor corrector 确定性校正结果）
        corrected = _extract_corrected_line_ids(rq)

        for f in ["question_number", "question_type", "answer",
                   "stem_line_ids", "options_line_ids", "answer_line_ids"]:
            fields[f][1] += 1
            e = gq.get(f)
            if f == "answer":
                a = rq.get(f)
                if normalize_answer_text(e) == normalize_answer_text(a):
                    fields[f][0] += 1
            elif f == "options_line_ids":
                qt = rq.get("question_type", "")
                if qt in ("fill_blank", "fill_in"):
                    fields[f][0] += 1
                else:
                    a = corrected["options_line_ids"]
                    if a and e and isinstance(a, dict) and isinstance(e, dict):
                        if _compare_options_line_ids(a, e):
                            fields[f][0] += 1
            elif f.endswith("_line_ids"):
                a = corrected[f]
                if a and e and sorted(a) == sorted(e):
                    fields[f][0] += 1
            else:
                a = rq.get(f)
                if a == e:
                    fields[f][0] += 1
        ec = gq.get("expected_content", {})
        if ec.get("stem"):
            fields["stem_content"][1] += 1
            rs = _Q_PREFIX_RE.sub("", rq.get("stem") or "").strip()
            es = _Q_PREFIX_RE.sub("", ec["stem"]).strip()
            if es in rs:
                fields["stem_content"][0] += 1
        if ec.get("options") and rq.get("options"):
            fields["options_content"][1] += 1
            ro = {o["label"]: o["text"] for o in rq["options"]}
            # 归一化空白后比较（不同 OCR 引擎的空格差异不影响语义）
            def _norm_ws(s: str) -> str:
                return re.sub(r'\s+', '', s)
            if all(_norm_ws(ec["options"][k]) in _norm_ws(ro.get(k, "")) for k in ec["options"]):
                fields["options_content"][0] += 1
        if gq.get("sub_questions"):
            fields["sub_questions_count"][1] += 1
            expected_subs = gq.get("sub_questions") or []
            actual_subs = rq.get("sub_questions") or []
            if len(expected_subs) == len(actual_subs):
                fields["sub_questions_count"][0] += 1

            fields["sub_question_options_line_ids"][1] += 1
            if _compare_sub_questions(rq, gq):
                fields["sub_question_options_line_ids"][0] += 1
        if gq.get("options_line_ids"):
            fields["option_completeness"][1] += 1
            if _option_completeness_correct(rq):
                fields["option_completeness"][0] += 1
    return fields


def evaluate_pipeline_health(result_dict, l1_document=None):
    """评估管道健康指标。"""
    health = {
        "anchor_status_dist": Counter(),
        "provenance_sources": Counter(),
        "quality_confidence_dist": {"high": 0, "medium": 0, "low": 0},
        "blocked_count": 0,
        "dual_source_lines": 0,
        "arbitration_source_dist": Counter(),  # 仅统计双源行的仲裁结果
        "arbitration_count": 0,  # 有 dual_source 且被仲裁的行数
        "llm_violations": 0,     # LLM 返回非法内容的行数
        "conflict_count": 0,     # 有双源冲突的行数
        "total_questions": len(result_dict.get("questions", [])),
        "answer_matched": 0,
        "answer_empty": 0,
    }
    for stage in result_dict.get("stages", []):
        if stage.get("name") == "dual_source_merge":
            health["dual_source_lines"] = stage.get("dual_source_lines", 0)
            health["native_only_lines"] = stage.get("native_only_lines", 0)
        if stage.get("name") == "l1_arbiter":
            # 从 stage 读取真实审计统计
            health["conflict_count"] = stage.get("conflicts", 0)
            health["llm_audited"] = stage.get("llm_audited", 0)
    # 仲裁后 line source 分布（仅统计双源行）
    if l1_document:
        for line in l1_document.lines:
            raw = getattr(line, "raw_sources", None)
            if raw and isinstance(raw, dict) and len(raw) > 1:
                src = getattr(line, "selected_source", None) or line.source
                health["arbitration_source_dist"][src] += 1
                if getattr(line, "selected_source", None) == "llm_violation":
                    health["llm_violations"] += 1
    for q in result_dict.get("questions", []):
        if q.get("answer") is not None and str(q.get("answer", "")).strip():
            health["answer_matched"] += 1
        else:
            health["answer_empty"] += 1
        for ca in q.get("corrected_anchors", []):
            status = ca.get("anchor_status", "unknown")
            health["anchor_status_dist"][status] += 1
        ap = q.get("answer_provenance")
        if ap:
            health["provenance_sources"][ap.get("source", "unknown")] += 1
        ep = q.get("explanation_provenance")
        if ep:
            health["provenance_sources"][ep.get("source", "unknown")] += 1
        conf = q.get("confidence", 0)
        if conf >= 0.8:
            health["quality_confidence_dist"]["high"] += 1
        elif conf >= 0.5:
            health["quality_confidence_dist"]["medium"] += 1
        else:
            health["quality_confidence_dist"]["low"] += 1
        issues = q.get("issues", [])
        if any("禁止自动发布" in i for i in issues):
            health["blocked_count"] += 1
    return health


async def main():
    live_mode = "--live" in sys.argv
    live_pp_mode = "--live-pp" in sys.argv

    if live_pp_mode:
        mode_str = "LIVE-PP (smoke)"
    elif live_mode:
        mode_str = "LIVE (frozen PP + real LLM)"
    else:
        mode_str = "MOCK (frozen PP + MockLLM)"

    print(f"\n{'='*60}")
    print(f"Phase 1 Eval — {mode_str}")
    print(f"{'='*60}")

    golden = load_golden()
    fixture = load_fixture()

    # 构建 gateway
    if live_mode or live_pp_mode:
        from app.core.config import settings
        from app.ai.providers import HTTPLLMProvider
        providers = []
        if settings.deepseek_api_key and settings.deepseek_base_url:
            providers.append(HTTPLLMProvider(
                name="deepseek", base_url=settings.deepseek_base_url,
                api_key=settings.deepseek_api_key, model=settings.deepseek_model,
                timeout_seconds=300,
            ))
        if not providers:
            print("ERROR: No live LLM providers configured in backend/.env")
            return 1
        gateway = LLMGateway(mode="live", providers=providers)
        print(f"Using LLM: {providers[0].name} ({providers[0].model})")
    else:
        gateway = LLMGateway(mode="live", providers=[
            MockLLMProvider(response=build_mock_response(golden))
        ])

    # 构建 L1 文档
    if live_pp_mode:
        # 真实 PP smoke：不传预计算文档，让 pipeline 调用真实 OCR
        kwargs = {"gateway": gateway, "pdf_path": PDF_PATH, "page_range": (1, 5)}
    elif live_mode:
        # live LLM + 冻结 PP + 真实 native fixture：触发真实双源合并和仲裁
        native_fixture = load_native_fixture()
        kwargs = {
            "gateway": gateway,
            "pdf_path": None,
            "ppsv3_doc": build_ppsv3_doc_from_fixture(fixture),
            "native_doc": build_native_doc_from_fixture(native_fixture),
        }
    else:
        # mock 模式：冻结 PP + 真实 native fixture，触发双源合并和仲裁
        native_fixture = load_native_fixture()
        kwargs = {
            "gateway": gateway,
            "pdf_path": None,
            "ppsv3_doc": build_ppsv3_doc_from_fixture(fixture),
            "native_doc": build_native_doc_from_fixture(native_fixture),
        }

    # live-pp smoke 跑 3 次取最差
    smoke_runs = 3 if live_pp_mode else 1
    results = []
    for run_idx in range(smoke_runs):
        if smoke_runs > 1:
            print(f"\n--- Run {run_idx + 1}/{smoke_runs} ---")
        r = await run_pipeline(**kwargs)
        results.append(r)

    # 取最差结果（按字段准确率最低的那次）
    worst_result = results[0]
    worst_acc = None
    for r in results:
        rqs_candidate = r.to_dict()["questions"]
        acc_candidate = evaluate_accuracy(rqs_candidate, golden)
        # 用总准确率最低的作为 worst
        total = sum(c for c, t in acc_candidate.values())
        total_max = sum(t for c, t in acc_candidate.values())
        if worst_acc is None or total < sum(c for c, t in worst_acc.values()):
            worst_acc = acc_candidate
            worst_result = r

    result = worst_result

    # 验证 line_id 引用的结构一致性
    if live_pp_mode:
        valid_ids = {l.line_id for l in result.l1_document.lines}
    else:
        valid_ids = {l["line_id"] for l in fixture["lines"]}
    line_errors = sum(
        1 for q in golden["questions"]
        for lid in q.get("stem_line_ids", []) + q.get("answer_line_ids", [])
        if lid not in valid_ids
    )

    # 保存结果（保存最差那次）
    mode_file = "live_pp" if live_pp_mode else ("live" if live_mode else "mock")
    out = ROOT / "test" / "results" / f"phase1_{mode_file}_result.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Results saved to: {out}")

    rqs = result.to_dict()["questions"]

    # 字段级准确率
    acc = evaluate_accuracy(rqs, golden)
    print(f"\nQuestions: {len(rqs)}, Time: {result.total_time_ms}ms")
    print(f"Line ID errors: {line_errors}, Pipeline errors: {len(result.errors)}")
    for f, (c, t) in acc.items():
        a = c / t if t else 0
        print(f"  {f}: {c}/{t} = {a:.1%}")

    # 管道健康指标
    health = evaluate_pipeline_health(result.to_dict(), result.l1_document)
    print(f"\nPipeline health:")
    print(f"  dual_source_lines: {health['dual_source_lines']}")
    print(f"  native_only_lines: {health.get('native_only_lines', 0)}")
    print(f"  llm_audited: {health.get('llm_audited', 0)}")
    print(f"  conflict_count: {health['conflict_count']}")
    print(f"  llm_violations: {health['llm_violations']}")
    print(f"  anchor_status: {dict(health['anchor_status_dist'])}")
    print(f"  provenance: {dict(health['provenance_sources'])}")
    print(f"  quality: {health['quality_confidence_dist']}")
    print(f"  blocked: {health['blocked_count']}")
    print(f"  answer_matched: {health['answer_matched']}")
    print(f"  answer_empty: {health['answer_empty']}")

    sources = Counter(r.get("answer_provenance", {}).get("source", "none") for r in rqs)
    print(f"  answer_sources: {dict(sources)}")
    print(f"  arbitration_sources: {dict(health['arbitration_source_dist'])}")

    # explanation 检查
    expl_empty = sum(1 for q in golden["questions"] if not q.get("explanation_line_ids"))
    expl_fallback = sum(1 for q in golden["questions"]
                        if not q.get("explanation_line_ids") and q.get("explanation_source") == "llm_fallback")
    expl_with_lines = sum(1 for q in golden["questions"] if q.get("explanation_line_ids"))
    if expl_empty:
        print(f"explanation: {expl_empty} questions without inline explanation "
              f"(source=llm_fallback: {expl_fallback}, with line_ids: {expl_with_lines})")
    # 检查没有详解的题必须标记为 llm_fallback
    expl_bad_source = sum(1 for q in golden["questions"]
                          if not q.get("explanation_line_ids") and q.get("explanation_source") != "llm_fallback")
    if expl_bad_source > 0:
        failed.append(f"explanation without inline lines but source != llm_fallback: {expl_bad_source}")

    # 验收判定
    if live_pp_mode:
        thresholds = THRESHOLDS_SMOKE
    elif live_mode:
        thresholds = THRESHOLDS_LIVE
    else:
        thresholds = THRESHOLDS_EXACT
    failed = []
    for f, th in thresholds.items():
        c, t = acc.get(f, [0, 0])
        a = c / t if t else 0
        if a < th:
            failed.append(f"{f} {a:.1%} < {th:.0%}")

    # 全卷验收阈值检查（仅 live-pp smoke 模式）
    if live_pp_mode:
        answer_matched = health.get("answer_matched", 0)
        blocked_count = health["blocked_count"]
        quality_high = health["quality_confidence_dist"]["high"]
        missing_anchors = health["anchor_status_dist"].get("missing", 0)

        if answer_matched < THRESHOLDS_FULL卷["min_answer_matched"]:
            failed.append(f"full卷 answer_matched: {answer_matched} < {THRESHOLDS_FULL卷['min_answer_matched']}")
        if blocked_count > THRESHOLDS_FULL卷["max_blocked"]:
            failed.append(f"full卷 blocked: {blocked_count} > {THRESHOLDS_FULL卷['max_blocked']}")
        if quality_high < THRESHOLDS_FULL卷["min_quality_high"]:
            failed.append(f"full卷 quality_high: {quality_high} < {THRESHOLDS_FULL卷['min_quality_high']}")
        if missing_anchors > THRESHOLDS_FULL卷["max_missing_anchors"]:
            failed.append(f"full卷 missing_anchors: {missing_anchors} > {THRESHOLDS_FULL卷['max_missing_anchors']}")

    # anchor_status 检查
    missing_count = health["anchor_status_dist"].get("missing", 0)
    retry_count = health["anchor_status_dist"].get("retry", 0)
    # live-pp smoke 允许 missing（答案表条目会被 LLM 误检为题目，无选项锚点）
    max_missing = 0 if not live_pp_mode else 10
    if missing_count > max_missing:
        failed.append(f"anchor missing: {missing_count} > {max_missing}")
    # live 模式允许少量 retry（LLM 粗定位偏移是预期行为，V1_LESSONS 3.1a）
    max_retry = 0 if not (live_mode or live_pp_mode) else 10
    if retry_count > max_retry:
        failed.append(f"anchor retry: {retry_count} > {max_retry}")

    # 仲裁验证：dual_source_lines > 0 时，必须有真实仲裁活动
    arb_src = health["arbitration_source_dist"]
    if health["dual_source_lines"] > 0 and len(arb_src) > 0:
        # 1. live-pp smoke 允许仲裁 no-op（PP OCR 结果可能始终优于 native）
        if not live_pp_mode and len(arb_src) == 1:
            failed.append(f"arbitration no-op: all lines selected {list(arb_src.keys())[0]}")
        # 2. 冲突数必须 > 0（有 dual_source 但无冲突说明 merge 假阳性）
        conflict_count = health.get("conflict_count", 0)
        if conflict_count == 0 and health["dual_source_lines"] > 0:
            failed.append("arbitration: dual_source_lines > 0 but conflicts == 0 (merge may be fake)")
        # 3. LLM violation 检查
        llm_violations = health.get("llm_violations", 0)
        if llm_violations > 0:
            failed.append(f"arbitration LLM violations: {llm_violations}")
        # 4. 仲裁后来源分布必须包含 ppsv3（native 过多说明仲裁偏向 native fallback）
        if "ppsv3" not in arb_src and health["dual_source_lines"] > 5:
            failed.append("arbitration: no ppsv3 selections — arbiter may always fallback to native")

    # source_provenance 检查
    no_provenance = sum(1 for q in rqs if not q.get("answer_provenance"))
    if no_provenance > 0:
        failed.append(f"answer_provenance empty: {no_provenance}")

    # line_errors 检查（live-pp smoke 允许少量偏移）
    if not live_pp_mode and line_errors > 0:
        failed.append(f"line_id errors: {line_errors}")

    ok = not failed and not result.errors
    print(f"\n{'='*60}")
    print(f"{'PASS' if ok else 'FAIL'}: Phase 1 ({mode_str})")
    if failed:
        for f in failed:
            print(f"  FAIL: {f}")
    print(f"{'='*60}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

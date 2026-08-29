#!/usr/bin/env python3
"""综合题验证脚本：9 科各 1 份 PDF，验证 composite question 支持。

重点验证：
1. 丢弃率是否下降（英语 32.6% → <10%）
2. 英语 3 篇阅读是否被正确分为 3 道综合题（DSH Q1）
3. is_composite / sub_questions 字段正确输出

用法：
  cd D:\\Project\\AITutors-v2
  python test/scripts/run_composite_validation.py --runs 1

输出：
  test/results/composite_validation/{stem}_run{N}.json
  test/results/composite_validation/summary.json
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "test" / "scripts"))

_backend_env = ROOT / "backend" / ".env"
if _backend_env.exists():
    for line in _backend_env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())

from app.domains.document.simple_pipeline import run_simple_pipeline
from run_live_validation import build_live_gateway


PDF_DIR = ROOT / "test" / "pdf"
OUTPUT_DIR = ROOT / "test" / "results" / "composite_validation"

# 每科 1 份代表性 PDF
TARGET_FILES = [
    # 英语：含完形填空、语法填空、阅读理解（DSH Q1 重点）
    "2026北京东城高一（上）期末英语（教师版）.pdf",
    # 语文：含材料阅读、文言文阅读
    "2026北京八十中高一（上）期末语文（教师版）.pdf",
    # 数学：独立选择题为主
    "2026北京二中高一（上）期末数学（教师版）.pdf",
    # 物理：综合实验题
    "2026北京丰台高一（上）期末物理（教师版）.pdf",
    # 化学：工艺流程、实验综合
    "2026北京八一学校高一（上）期末化学（教师版）.pdf",
    # 生物：实验设计题
    "2026北京北师大附中高一（上）期末生物（教师版）.pdf",
    # 历史：材料分析题
    "2025北京东城高一（上）期末历史（教师版）.pdf",
    # 政治：材料分析题
    "2026北京东城高一（上）期末政治（教师版）.pdf",
    # 地理：材料分析题
    "2026北京朝阳高一（上）期末地理（教师版）.pdf",
]


def _analyze_composite_questions(data: dict) -> dict:
    """分析综合题统计信息。"""
    questions = data.get("questions", [])
    composites = [q for q in questions if q.get("is_composite")]
    non_composites = [q for q in questions if not q.get("is_composite")]

    # 子题统计
    total_sub_questions = 0
    for q in composites:
        subs = q.get("sub_questions", [])
        total_sub_questions += len(subs)

    # 合并统计：有 shared_material_line_ids 但未标记为 composite 的题目
    shared_material_only = [
        q for q in non_composites
        if q.get("shared_material_line_ids")
    ]

    return {
        "total_questions": len(questions),
        "composite_count": len(composites),
        "non_composite_count": len(non_composites),
        "total_sub_questions": total_sub_questions,
        "shared_material_only_count": len(shared_material_only),
    }


def _check_english_reading_composites(data: dict) -> list[str]:
    """DSH Q1：检查英语阅读理解是否被正确分组。

    英语通常有 3 篇阅读理解（A/B/C），每篇 3-4 题，
    应该被合并为 3 道综合题，而不是 1 道。
    """
    warnings = []
    questions = data.get("questions", [])

    # 找出所有阅读理解综合题
    reading_composites = [
        q for q in questions
        if q.get("is_composite") and q.get("question_type") in (
            "reading", "cloze", "seven_to_five", "single_choice", "fill_in"
        )
    ]

    if not reading_composites:
        return warnings

    # 检查是否有过多的子题（可能误合并）
    max_sub_questions_by_type = {
        "cloze": 15,
        "reading": 6,
        "seven_to_five": 8,
    }
    for qc in reading_composites:
        subs = qc.get("sub_questions", [])
        limit = max_sub_questions_by_type.get(qc.get("question_type"), 6)
        if len(subs) > limit:
            warnings.append(
                f"Q1: 综合题 {qc['question_number']} 有 {len(subs)} 个子题，"
                f"可能是多篇阅读被误合并"
            )

    # 检查是否有多个阅读综合题共享材料行
    material_sets = []
    for qc in reading_composites:
        mat = set(qc.get("shared_material_line_ids", []))
        if mat:
            material_sets.append((qc["question_number"], mat))

    for i in range(len(material_sets)):
        for j in range(i + 1, len(material_sets)):
            q1, s1 = material_sets[i]
            q2, s2 = material_sets[j]
            overlap = s1 & s2
            if len(overlap) > 3:
                warnings.append(
                    f"Q1: 综合题 {q1} 和 {q2} 共享 {len(overlap)} 行材料，"
                    f"可能是误合并"
                )

    return warnings


async def run_one(pdf_path: Path, gateway, run_no: int) -> dict:
    print(
        f"[{time.strftime('%H:%M:%S')}] run {pdf_path.name} #{run_no}",
        flush=True,
    )
    started = time.perf_counter()
    try:
        result = await run_simple_pipeline(
            pdf_path,
            filename=pdf_path.name,
            gateway=gateway,
        )
        data = result.to_dict()
        data["_label"] = f"composite:{pdf_path.stem}:run{run_no}"
        data["_elapsed_s"] = round(time.perf_counter() - started, 1)

        # 综合题分析
        composite_stats = _analyze_composite_questions(data)
        data["_composite_stats"] = composite_stats

        # 英语阅读检查
        if "英语" in pdf_path.name:
            data["_english_reading_warnings"] = _check_english_reading_composites(data)

        ingest_summary = data.get("ingest_summary", {})
        ingested = ingest_summary.get("ingested", data["question_count"])
        discarded = ingest_summary.get("discarded", 0)

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out_path = OUTPUT_DIR / f"{pdf_path.stem}_run{run_no}.json"
        out_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # 打印摘要
        cs = composite_stats
        print(
            f"  -> {pdf_path.name} #{run_no}: status={data['status']} "
            f"questions={cs['total_questions']} "
            f"composite={cs['composite_count']} "
            f"sub_questions={cs['total_sub_questions']} "
            f"ingested={ingested} discarded={discarded} "
            f"elapsed={data['_elapsed_s']}s",
            flush=True,
        )

        # 打印英语阅读警告
        if data.get("_english_reading_warnings"):
            for w in data["_english_reading_warnings"]:
                print(f"  WARNING: {w}", flush=True)

        return {
            "filename": pdf_path.name,
            "run": run_no,
            "status": data["status"],
            "question_count": cs["total_questions"],
            "composite_count": cs["composite_count"],
            "sub_question_count": cs["total_sub_questions"],
            "ingested": ingested,
            "discarded": discarded,
            "discard_rate": (
                round(discarded / data["question_count"], 4)
                if data["question_count"]
                else 1.0
            ),
            "discard_reasons": ingest_summary.get("discard_reasons", {}),
            "elapsed_s": data["_elapsed_s"],
            "warnings": data.get("_english_reading_warnings", []),
            "path": str(out_path),
        }
    except Exception as exc:
        elapsed = round(time.perf_counter() - started, 1)
        print(
            f"  -> {pdf_path.name} #{run_no}: FAILED ({elapsed}s) {exc}",
            flush=True,
        )
        return {
            "filename": pdf_path.name,
            "run": run_no,
            "status": "failed",
            "error": str(exc),
            "elapsed_s": elapsed,
        }


async def main() -> int:
    parser = argparse.ArgumentParser(description="Composite question validation")
    parser.add_argument("--runs", type=int, default=1, help="runs per PDF")
    parser.add_argument(
        "--file", type=str, default=None,
        help="仅跑文件名包含该子串的 PDF（如 --file 英语）",
    )
    parser.add_argument(
        "--subjects", type=str, default=None,
        help="逗号分隔的科目过滤（如 --subjects 数学,化学）",
    )
    parser.add_argument(
        "--ocr-model", type=str, default=None,
        help="覆盖 OCR 模型（如 --ocr-model PaddleOCR-VL）",
    )
    args = parser.parse_args()

    # OCR 模型覆盖：通过环境变量传递给 simple_pipeline
    if args.ocr_model:
        os.environ["OCR_MODEL_OVERRIDE"] = args.ocr_model

    gateway = build_live_gateway()
    if gateway is None:
        print("ERROR: live gateway unavailable", file=sys.stderr)
        return 1

    subject_filters = [
        item.strip()
        for item in (args.subjects or "").split(",")
        if item.strip()
    ]
    summary = []
    targets = [
        f for f in TARGET_FILES
        if (not args.file or args.file in f)
        and (
            not subject_filters
            or any(subject in f for subject in subject_filters)
        )
    ]
    if not targets:
        print(f"WARNING: no target matches --file {args.file!r}", file=sys.stderr)
        return 1
    for filename in targets:
        pdf_path = PDF_DIR / filename
        if not pdf_path.exists():
            print(f"WARNING: {filename} not found, skipping", flush=True)
            continue
        for run_no in range(1, max(1, args.runs) + 1):
            summary.append(await run_one(pdf_path, gateway, run_no))
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            summary_path = OUTPUT_DIR / "summary.json"
            summary_path.write_text(
                json.dumps(summary, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    # 打印总结
    print("\n" + "=" * 70, flush=True)
    print("综合题验证总结", flush=True)
    print("=" * 70, flush=True)

    succeeded = [r for r in summary if r["status"] == "succeeded"]
    failed = [r for r in summary if r["status"] == "failed"]

    if succeeded:
        print("\n✅ 成功:", flush=True)
        for r in succeeded:
            print(
                f"  {r['filename']} run{r['run']}: "
                f"questions={r['question_count']} "
                f"composite={r['composite_count']} "
                f"sub_q={r['sub_question_count']} "
                f"ingested={r['ingested']} "
                f"discarded={r['discarded']} "
                f"rate={r['discard_rate']:.1%} "
                f"elapsed={r['elapsed_s']}s",
                flush=True,
            )
            if r.get("warnings"):
                for w in r["warnings"]:
                    print(f"    ⚠️  {w}", flush=True)

    if failed:
        print("\n❌ 失败:", flush=True)
        for r in failed:
            print(
                f"  {r['filename']} run{r['run']}: {r.get('error', 'unknown')}",
                flush=True,
            )

    # 汇总统计
    if succeeded:
        total_q = sum(r["question_count"] for r in succeeded)
        total_composite = sum(r["composite_count"] for r in succeeded)
        total_sub_q = sum(r["sub_question_count"] for r in succeeded)
        total_ingested = sum(r["ingested"] for r in succeeded)
        total_discarded = sum(r["discarded"] for r in succeeded)
        overall_rate = total_discarded / total_q if total_q else 0

        print(f"\n📊 汇总:", flush=True)
        print(f"  总题目数: {total_q}", flush=True)
        if total_q:
            print(f"  综合题数: {total_composite} ({total_composite/total_q:.1%})", flush=True)
        print(f"  子题总数: {total_sub_q}", flush=True)
        print(f"  入库数: {total_ingested}", flush=True)
        print(f"  丢弃数: {total_discarded}", flush=True)
        print(f"  丢弃率: {overall_rate:.1%}", flush=True)

    print(f"\n📁 详细结果: {OUTPUT_DIR}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

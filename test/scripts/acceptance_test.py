#!/usr/bin/env python3
"""系统功能验收测试 — 9份全新PDF全流程验收。

流程：PDF → OCR → LLM标注 → LLM答案提取 → 入库
每个关键节点记录日志，处理过程中只记录不动手。

用法：
  python acceptance_test.py                    # 全部9份
  python acceptance_test.py --limit 3          # 前3份
  python acceptance_test.py --subject 物理      # 只跑物理

输出：
  test/results/acceptance/{filename}_result.json  — 每份完整结果
  test/results/acceptance/summary.json            — 汇总
  test/results/acceptance/acceptance.log          — 详细日志
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "test" / "scripts"))

# 加载 .env
_backend_env = ROOT / "backend" / ".env"
if _backend_env.exists():
    for line in _backend_env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

from app.domains.document.simple_pipeline import run_simple_pipeline, _extract_subject_from_filename, _ocr_model_for_subject
from app.domains.document.answer_extractor import extract_answers_from_markdown
from run_live_validation import build_live_gateway

PDF_DIR = ROOT / "test" / "pdf" / "new"
OUTPUT_DIR = ROOT / "test" / "results" / "acceptance"
LOG_FILE = OUTPUT_DIR / "acceptance.log"


def setup_logging():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


async def run_one(pdf_path: Path, gateway, idx: int, total: int) -> dict:
    """单份PDF全流程验收。"""
    filename = pdf_path.name
    stem = pdf_path.stem
    subject = _extract_subject_from_filename(filename)
    ocr_model = _ocr_model_for_subject(subject)

    logger = logging.getLogger(__name__)
    logger.info("=" * 80)
    logger.info("[%d/%d] 开始处理: %s", idx, total, filename)
    logger.info("  学科: %s, OCR模型: %s", subject, ocr_model)
    logger.info("=" * 80)

    result = {
        "filename": filename,
        "subject": subject,
        "ocr_model": ocr_model,
        "stages": {},
        "errors": [],
    }

    # ── Stage 1: 管线执行（OCR + LLM标注 + 切片 + 答案匹配 + 质量门）──
    logger.info("[Stage 1] 执行管线（OCR → LLM标注 → 切片 → 答案匹配 → 质量门）")
    t1 = time.perf_counter()

    try:
        pipeline_result = await run_simple_pipeline(
            pdf_path=pdf_path,
            filename=filename,
            subject=subject,
            ocr_model=ocr_model,
            gateway=gateway,
        )
        elapsed_ms = int((time.perf_counter() - t1) * 1000)

        pipeline_dict = pipeline_result.to_dict()
        result["stages"]["pipeline"] = {
            "status": pipeline_result.status,
            "elapsed_ms": elapsed_ms,
            "question_count": len(pipeline_result.sliced_questions),
            "ingested": pipeline_dict.get("ingest_summary", {}).get("ingested", 0),
            "discarded": pipeline_dict.get("ingest_summary", {}).get("discarded", 0),
            "errors": pipeline_result.errors,
        }

        logger.info("[Stage 1] 管线完成: status=%s, questions=%d, elapsed=%dms",
                     pipeline_result.status, len(pipeline_result.sliced_questions), elapsed_ms)

        if pipeline_result.status == "failed":
            logger.error("[Stage 1] 管线失败: %s", pipeline_result.errors)
            result["errors"].append(f"pipeline failed: {pipeline_result.errors}")
            return result

    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - t1) * 1000)
        logger.error("[Stage 1] 管线异常: %s", exc)
        result["stages"]["pipeline"] = {"status": "exception", "error": str(exc), "elapsed_ms": elapsed_ms}
        result["errors"].append(f"pipeline exception: {exc}")
        return result

    # ── Stage 2: LLM 答案提取 ──
    logger.info("[Stage 2] LLM 答案提取")
    t2 = time.perf_counter()

    ocr_markdown = None
    if pipeline_result.l1_document:
        ocr_markdown = "\n".join(line.text for line in pipeline_result.l1_document.lines)

    answer_result = None
    if ocr_markdown:
        try:
            answer_result = await extract_answers_from_markdown(
                ocr_markdown, gateway=gateway, filename=filename,
            )
            elapsed_ms = int((time.perf_counter() - t2) * 1000)

            result["stages"]["answer_extraction"] = {
                "status": "success" if answer_result.ok else "failed",
                "subject": answer_result.subject,
                "total": answer_result.total,
                "verified": answer_result.verified_count,
                "with_answer": answer_result.with_answer_count,
                "elapsed_ms": elapsed_ms,
                "error": answer_result.error,
            }

            logger.info("[Stage 2] 答案提取完成: subject=%s, total=%d, verified=%d, with_answer=%d, elapsed=%dms",
                         answer_result.subject, answer_result.total, answer_result.verified_count,
                         answer_result.with_answer_count, elapsed_ms)

            if not answer_result.ok:
                logger.warning("[Stage 2] 答案提取失败: %s", answer_result.error)
                result["errors"].append(f"answer_extraction failed: {answer_result.error}")

        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - t2) * 1000)
            logger.error("[Stage 2] 答案提取异常: %s", exc)
            result["stages"]["answer_extraction"] = {"status": "exception", "error": str(exc), "elapsed_ms": elapsed_ms}
            result["errors"].append(f"answer_extraction exception: {exc}")
    else:
        logger.warning("[Stage 2] 无 OCR markdown，跳过答案提取")
        result["stages"]["answer_extraction"] = {"status": "skipped", "reason": "no ocr_markdown"}

    # ── Stage 3: 三份文档持久化（记录大小） ──
    logger.info("[Stage 3] 文档持久化检查")
    native_size = 0
    if pipeline_result.native_l1_document:
        native_size = sum(len(line.text) for line in pipeline_result.native_l1_document.lines)
    ocr_size = len(ocr_markdown) if ocr_markdown else 0

    llm_annotated_size = 0
    if pipeline_result.l2_annotation:
        llm_annotated_json = json.dumps({
            "questions": [
                {"question_number": q.question_number, "question_type": q.question_type}
                for q in pipeline_result.l2_annotation.questions
            ]
        }, ensure_ascii=False)
        llm_annotated_size = len(llm_annotated_json)

    result["stages"]["document_persist"] = {
        "native_markdown_chars": native_size,
        "ocr_markdown_chars": ocr_size,
        "llm_annotated_chars": llm_annotated_size,
    }
    logger.info("[Stage 3] 文档大小: native=%d, ocr=%d, llm_annotated=%d chars",
                 native_size, ocr_size, llm_annotated_size)

    # ── Stage 4: 入库模拟（检查数据完整性） ──
    logger.info("[Stage 4] 入库数据完整性检查")
    questions_for_ingestion = []
    for sq in pipeline_result.sliced_questions:
        llm_answer = None
        if answer_result and answer_result.answers:
            llm_answer = answer_result.answers.get(str(sq.question_number))

        final_answer = ""
        final_explanation = ""
        answer_source = "none"

        if llm_answer and llm_answer.answer.strip():
            final_answer = llm_answer.answer
            final_explanation = llm_answer.explanation or sq.explanation or ""
            answer_source = "llm_extracted"
        elif sq.answer:
            final_answer = sq.answer
            final_explanation = sq.explanation or ""
            answer_source = "pipeline_sliced"

        is_high_conf = sq.confidence >= 0.8
        is_blocked = any("禁止自动发布" in i for i in (sq.issues or []))
        has_stem = bool((sq.stem or "").strip())

        if has_stem and is_high_conf and not is_blocked and final_answer.strip():
            status = "approved"
        elif has_stem:
            status = "reviewing"
        else:
            status = "skipped"

        questions_for_ingestion.append({
            "question_number": sq.question_number,
            "question_type": sq.question_type,
            "stem_preview": (sq.stem or "")[:80],
            "answer_preview": final_answer[:80],
            "answer_source": answer_source,
            "confidence": round(sq.confidence, 3),
            "status": status,
            "issues": sq.issues or [],
        })

    approved = sum(1 for q in questions_for_ingestion if q["status"] == "approved")
    reviewing = sum(1 for q in questions_for_ingestion if q["status"] == "reviewing")
    skipped = sum(1 for q in questions_for_ingestion if q["status"] == "skipped")

    result["stages"]["ingestion_preview"] = {
        "total": len(questions_for_ingestion),
        "approved": approved,
        "reviewing": reviewing,
        "skipped": skipped,
        "answer_source_llm": sum(1 for q in questions_for_ingestion if q["answer_source"] == "llm_extracted"),
        "answer_source_pipeline": sum(1 for q in questions_for_ingestion if q["answer_source"] == "pipeline_sliced"),
        "answer_source_none": sum(1 for q in questions_for_ingestion if q["answer_source"] == "none"),
    }
    result["questions"] = questions_for_ingestion

    logger.info("[Stage 4] 入库预览: total=%d, approved=%d, reviewing=%d, skipped=%d",
                 len(questions_for_ingestion), approved, reviewing, skipped)
    logger.info("[Stage 4] 答案来源: llm=%d, pipeline=%d, none=%d",
                 result["stages"]["ingestion_preview"]["answer_source_llm"],
                 result["stages"]["ingestion_preview"]["answer_source_pipeline"],
                 result["stages"]["ingestion_preview"]["answer_source_none"])

    # ── Stage 5: 质量统计 ──
    logger.info("[Stage 5] 质量统计")
    result["stages"]["quality"] = {
        "high_confidence": sum(1 for q in questions_for_ingestion if q["confidence"] >= 0.8),
        "low_confidence": sum(1 for q in questions_for_ingestion if q["confidence"] < 0.5),
        "blocked": sum(1 for q in questions_for_ingestion if any("禁止自动发布" in i for i in q["issues"])),
        "answer_missing": sum(1 for q in questions_for_ingestion if q["answer_source"] == "none"),
    }
    logger.info("[Stage 5] 质量: high_conf=%d, low_conf=%d, blocked=%d, answer_missing=%d",
                 result["stages"]["quality"]["high_confidence"],
                 result["stages"]["quality"]["low_confidence"],
                 result["stages"]["quality"]["blocked"],
                 result["stages"]["quality"]["answer_missing"])

    logger.info("=" * 80)
    logger.info("[%d/%d] 完成: %s — approved=%d, reviewing=%d, skipped=%d, errors=%d",
                idx, total, filename, approved, reviewing, skipped, len(result["errors"]))
    logger.info("=" * 80)

    return result


async def main() -> int:
    setup_logging()
    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(description="系统功能验收测试")
    parser.add_argument("--limit", type=int, default=None, help="最多处理份数")
    parser.add_argument("--subject", type=str, default=None, help="只处理指定学科")
    args = parser.parse_args()

    gateway = build_live_gateway()
    if gateway is None:
        logger.error("live gateway unavailable")
        return 1

    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    if args.subject:
        pdfs = [p for p in pdfs if args.subject in p.name]
    if args.limit:
        pdfs = pdfs[:args.limit]

    if not pdfs:
        logger.error("No PDF files found in %s", PDF_DIR)
        return 1

    logger.info("=" * 80)
    logger.info("系统功能验收测试开始")
    logger.info("PDF目录: %s", PDF_DIR)
    logger.info("待处理: %d 份", len(pdfs))
    logger.info("=" * 80)

    summary = []
    for idx, pdf_path in enumerate(pdfs, 1):
        result = await run_one(pdf_path, gateway, idx, len(pdfs))
        summary.append(result)

        # 保存单份结果
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out_path = OUTPUT_DIR / f"{pdf_path.stem}_result.json"
        out_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # 更新汇总
        summary_path = OUTPUT_DIR / "summary.json"
        summary_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # 最终汇总
    logger.info("=" * 80)
    logger.info("验收测试完成")
    logger.info("=" * 80)

    total_questions = 0
    total_approved = 0
    total_reviewing = 0
    total_errors = 0

    for r in summary:
        s = r.get("stages", {}).get("ingestion_preview", {})
        total_questions += s.get("total", 0)
        total_approved += s.get("approved", 0)
        total_reviewing += s.get("reviewing", 0)
        total_errors += len(r.get("errors", []))

        logger.info("  %s: %d题, approved=%d, reviewing=%d, errors=%d",
                     r["filename"], s.get("total", 0), s.get("approved", 0),
                     s.get("reviewing", 0), len(r.get("errors", [])))

    logger.info("-" * 80)
    logger.info("总计: %d份, %d题, approved=%d, reviewing=%d, errors=%d",
                len(summary), total_questions, total_approved, total_reviewing, total_errors)

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

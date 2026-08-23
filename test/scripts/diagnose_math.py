#!/usr/bin/env python3
"""诊断数学试卷：单独跑一次，记录每一步细节。"""

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

_backend_env = ROOT / "backend" / ".env"
if _backend_env.exists():
    for line in _backend_env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

from app.domains.document.simple_pipeline import run_simple_pipeline
from app.domains.document.answer_extractor import extract_answers_from_markdown
from run_live_validation import build_live_gateway

PDF_PATH = ROOT / "test" / "pdf" / "new" / "2026北京育才学校高一（上）期末数学（教师版）.pdf"
OUTPUT_DIR = ROOT / "test" / "results" / "diagnose_math"


async def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    gateway = build_live_gateway()

    logger = logging.getLogger(__name__)
    logger.info("=" * 80)
    logger.info("数学试卷诊断开始: %s", PDF_PATH.name)
    logger.info("=" * 80)

    # Stage 1: Pipeline
    logger.info("[Stage 1] 执行管线")
    t1 = time.perf_counter()
    pipeline_result = await run_simple_pipeline(
        pdf_path=PDF_PATH,
        filename=PDF_PATH.name,
        subject="数学",
        gateway=gateway,
    )
    elapsed = int((time.perf_counter() - t1) * 1000)
    logger.info("[Stage 1] 完成: status=%s, questions=%d, elapsed=%dms",
                pipeline_result.status, len(pipeline_result.sliced_questions), elapsed)

    # 详细检查每道题
    logger.info("[Stage 1] 逐题检查:")
    for sq in pipeline_result.sliced_questions:
        stem_preview = (sq.stem or "")[:60].replace("\n", " ")
        answer_preview = (sq.answer or "")[:30]
        issues = sq.issues or []
        blocked = any("禁止自动发布" in i for i in issues)
        logger.info(
            "  Q%s: type=%s conf=%.2f stem='%s' answer='%s' blocked=%s issues=%s",
            sq.question_number, sq.question_type, sq.confidence,
            stem_preview, answer_preview, blocked, issues,
        )

    # 检查管线的 stage 详情
    logger.info("[Stage 1] Stage 详情:")
    for stage in pipeline_result.stages:
        logger.info("  %s: %s", stage.get("name"), {k: v for k, v in stage.items() if k != "name"})

    # Stage 2: Answer extraction
    ocr_markdown = None
    if pipeline_result.l1_document:
        ocr_markdown = "\n".join(line.text for line in pipeline_result.l1_document.lines)
        logger.info("[Stage 2] OCR markdown: %d chars", len(ocr_markdown))

    if ocr_markdown:
        logger.info("[Stage 2] LLM 答案提取")
        t2 = time.perf_counter()
        answer_result = await extract_answers_from_markdown(ocr_markdown, gateway=gateway, filename=PDF_PATH.name)
        elapsed = int((time.perf_counter() - t2) * 1000)
        logger.info("[Stage 2] 完成: status=%s, total=%d, verified=%d, elapsed=%dms",
                    "success" if answer_result.ok else "failed",
                    answer_result.total, answer_result.verified_count, elapsed)
        if answer_result.error:
            logger.warning("[Stage 2] 错误: %s", answer_result.error)

        # 逐题检查答案
        if answer_result.ok:
            logger.info("[Stage 2] 逐题答案:")
            for q_num, ans in sorted(answer_result.answers.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0):
                logger.info("  Q%s: answer='%s' verified=%s", q_num, ans.answer[:50], ans.verified)

    # 保存完整结果
    result = {
        "pipeline": {
            "status": pipeline_result.status,
            "question_count": len(pipeline_result.sliced_questions),
            "stages": pipeline_result.stages,
            "questions": [
                {
                    "number": sq.question_number,
                    "type": sq.question_type,
                    "confidence": round(sq.confidence, 3),
                    "stem_preview": (sq.stem or "")[:100],
                    "answer": sq.answer,
                    "issues": sq.issues,
                }
                for sq in pipeline_result.sliced_questions
            ],
        },
        "answer_extraction": {
            "status": "success" if answer_result.ok else "failed",
            "total": answer_result.total if answer_result else 0,
            "verified": answer_result.verified_count if answer_result else 0,
            "error": answer_result.error if answer_result else None,
        } if ocr_markdown else None,
    }

    out_path = OUTPUT_DIR / "math_diagnosis.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("结果保存到: %s", out_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

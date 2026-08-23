#!/usr/bin/env python3
"""重新跑验收失败的3份试卷：地理、数学、历史。"""

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
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

from app.domains.document.simple_pipeline import run_simple_pipeline, _extract_subject_from_filename
from app.domains.document.answer_extractor import extract_answers_from_markdown
from run_live_validation import build_live_gateway

FAILED_PDFS = [
    ROOT / "test" / "pdf" / "new" / "2026北京朝阳高一（上）期末地理（教师版）.pdf",
    ROOT / "test" / "pdf" / "new" / "2026北京育才学校高一（上）期末数学（教师版）.pdf",
    ROOT / "test" / "pdf" / "new" / "2026北京九中高一（上）期末历史（教师版）.pdf",
]

OUTPUT_DIR = ROOT / "test" / "results" / "acceptance_retry"


async def run_one(pdf_path: Path, gateway) -> dict:
    filename = pdf_path.name
    subject = _extract_subject_from_filename(filename)
    print(f"\n{'='*80}")
    print(f"Processing: {filename} (subject={subject})")
    print(f"{'='*80}")

    result = {"filename": filename, "subject": subject, "stages": {}, "errors": []}

    # Stage 1: Pipeline
    t1 = time.perf_counter()
    try:
        pipeline_result = await run_simple_pipeline(
            pdf_path=pdf_path, filename=filename, subject=subject, gateway=gateway,
        )
        elapsed = int((time.perf_counter() - t1) * 1000)
        result["stages"]["pipeline"] = {
            "status": pipeline_result.status,
            "elapsed_ms": elapsed,
            "question_count": len(pipeline_result.sliced_questions),
            "errors": pipeline_result.errors,
        }
        print(f"  Pipeline: status={pipeline_result.status}, questions={len(pipeline_result.sliced_questions)}, elapsed={elapsed}ms")
        if pipeline_result.errors:
            print(f"  Pipeline errors: {pipeline_result.errors}")
    except Exception as exc:
        elapsed = int((time.perf_counter() - t1) * 1000)
        result["stages"]["pipeline"] = {"status": "exception", "error": str(exc), "elapsed_ms": elapsed}
        result["errors"].append(f"pipeline: {exc}")
        print(f"  Pipeline EXCEPTION: {exc}")
        return result

    # Stage 2: Answer extraction
    ocr_markdown = None
    if pipeline_result.l1_document:
        ocr_markdown = "\n".join(line.text for line in pipeline_result.l1_document.lines)

    if ocr_markdown:
        t2 = time.perf_counter()
        try:
            answer_result = await extract_answers_from_markdown(ocr_markdown, gateway=gateway, filename=filename)
            elapsed = int((time.perf_counter() - t2) * 1000)
            result["stages"]["answer_extraction"] = {
                "status": "success" if answer_result.ok else "failed",
                "subject": answer_result.subject,
                "total": answer_result.total,
                "verified": answer_result.verified_count,
                "elapsed_ms": elapsed,
                "error": answer_result.error,
            }
            print(f"  Answer extraction: status={'success' if answer_result.ok else 'failed'}, total={answer_result.total}, verified={answer_result.verified_count}, elapsed={elapsed}ms")
            if answer_result.error:
                print(f"  Answer extraction error: {answer_result.error}")
        except Exception as exc:
            elapsed = int((time.perf_counter() - t2) * 1000)
            result["stages"]["answer_extraction"] = {"status": "exception", "error": str(exc), "elapsed_ms": elapsed}
            result["errors"].append(f"answer_extraction: {exc}")
            print(f"  Answer extraction EXCEPTION: {exc}")

    # Stage 3: Ingestion preview
    approved = sum(1 for sq in pipeline_result.sliced_questions
                   if sq.confidence >= 0.8
                   and not any("禁止自动发布" in i for i in (sq.issues or []))
                   and (sq.stem or "").strip())
    reviewing = len(pipeline_result.sliced_questions) - approved
    result["stages"]["ingestion_preview"] = {
        "total": len(pipeline_result.sliced_questions),
        "approved": approved,
        "reviewing": reviewing,
    }
    print(f"  Ingestion preview: total={len(pipeline_result.sliced_questions)}, approved={approved}, reviewing={reviewing}")

    return result


async def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    gateway = build_live_gateway()
    if gateway is None:
        print("ERROR: live gateway unavailable")
        return 1

    results = []
    for pdf_path in FAILED_PDFS:
        result = await run_one(pdf_path, gateway)
        results.append(result)

        out_path = OUTPUT_DIR / f"{pdf_path.stem}_retry_result.json"
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    summary_path = OUTPUT_DIR / "retry_summary.json"
    summary_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{'='*80}")
    print("Retry complete. Results saved to:")
    print(f"  {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

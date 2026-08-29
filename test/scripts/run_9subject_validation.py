#!/usr/bin/env python3
"""9-subject small validation: one teacher PDF per subject, one or more runs.

Output:
  test/results/9subject_validation/{stem}_run{N}.json
  test/results/9subject_validation/summary.json
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
OUTPUT_DIR = ROOT / "test" / "results" / "9subject_validation"

TARGET_FILES = [
    "2025北京东城高一（上）期末历史（教师版）.pdf",
    "2026北京东城高一（上）期末政治（教师版）.pdf",
    "2026北京东城高一（上）期末英语（教师版）.pdf",
    "2026北京八十中高一（上）期末语文（教师版）.pdf",
    "2026北京朝阳高一（上）期末地理（教师版）.pdf",
    "2026北京二中高一（上）期末数学（教师版）.pdf",
    "2026北京丰台高一（上）期末物理（教师版）.pdf",
    "2026北京八一学校高一（上）期末化学（教师版）.pdf",
    "2026北京北师大附中高一（上）期末生物（教师版）.pdf",
]


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
        data["_label"] = f"9subject:{pdf_path.stem}:run{run_no}"
        data["_elapsed_s"] = round(time.perf_counter() - started, 1)
        ingest_summary = data.get("ingest_summary", {})
        ingested = ingest_summary.get("ingested", data["question_count"])
        discarded = ingest_summary.get("discarded", 0)

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out_path = OUTPUT_DIR / f"{pdf_path.stem}_run{run_no}.json"
        out_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(
            f"  -> {pdf_path.name} #{run_no}: status={data['status']} "
            f"questions={data['question_count']} ingested={ingested} "
            f"discarded={discarded} elapsed={data['_elapsed_s']}s",
            flush=True,
        )
        return {
            "filename": pdf_path.name,
            "run": run_no,
            "status": data["status"],
            "question_count": data["question_count"],
            "ingested": ingested,
            "discarded": discarded,
            "discard_rate": (
                round(discarded / data["question_count"], 4)
                if data["question_count"]
                else 1.0
            ),
            "discard_reasons": ingest_summary.get("discard_reasons", {}),
            "elapsed_s": data["_elapsed_s"],
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
    parser = argparse.ArgumentParser(description="9-subject validation")
    parser.add_argument("--runs", type=int, default=1, help="runs per PDF")
    args = parser.parse_args()

    gateway = build_live_gateway()
    if gateway is None:
        print("ERROR: live gateway unavailable", file=sys.stderr)
        return 1

    summary = []
    for filename in TARGET_FILES:
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
            print(f"Summary updated: {summary_path}", flush=True)

    print("\n=== 9-subject summary ===", flush=True)
    for record in summary:
        if record["status"] == "succeeded":
            print(
                f"{record['filename']} run{record['run']}: "
                f"questions={record['question_count']} "
                f"ingested={record['ingested']} "
                f"discarded={record['discarded']} "
                f"rate={record['discard_rate']:.1%} "
                f"elapsed={record['elapsed_s']}s",
                flush=True,
            )
        else:
            print(
                f"{record['filename']} run{record['run']}: FAILED "
                f"{record.get('error', 'unknown')}",
                flush=True,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

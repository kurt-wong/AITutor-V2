#!/usr/bin/env python3
"""验证语义锚点对丰台物理、九中物理的效果。"""

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

from app.domains.document.simple_pipeline import run_simple_pipeline
from run_live_validation import build_live_gateway

PDF_DIR = ROOT / "test" / "pdf"
OUTPUT_DIR = ROOT / "test" / "results" / "physics_validation"


async def run_one(pdf_path: Path, gateway, run_no: int) -> dict:
    stem = pdf_path.stem
    print(f"[{time.strftime('%H:%M:%S')}] run {stem} #{run_no}", flush=True)
    started = time.perf_counter()
    try:
        result = await run_simple_pipeline(
            pdf_path,
            filename=pdf_path.name,
            gateway=gateway,
        )
        data = result.to_dict()
        data["_label"] = f"simple:{stem}:run{run_no}"
        data["_elapsed_s"] = round(time.perf_counter() - started, 1)
        ingest_summary = data.get("ingest_summary", {})
        ingested = ingest_summary.get("ingested", data["question_count"])
        discarded = ingest_summary.get("discarded", 0)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out_path = OUTPUT_DIR / f"{stem}_run{run_no}.json"
        out_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(
            f"  -> {stem} #{run_no}: status={data['status']} "
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
            "discard_rate": round(discarded / data["question_count"], 4) if data["question_count"] else 1.0,
            "elapsed_s": data["_elapsed_s"],
            "path": str(out_path),
        }
    except Exception as e:
        elapsed = round(time.perf_counter() - started, 1)
        print(f"  -> {stem} #{run_no}: FAILED ({elapsed}s) {e}", flush=True)
        return {
            "filename": pdf_path.name,
            "run": run_no,
            "status": "failed",
            "error": str(e),
            "elapsed_s": elapsed,
        }


async def main() -> int:
    gateway = build_live_gateway()
    if gateway is None:
        print("ERROR: live gateway unavailable", file=sys.stderr)
        return 1

    # 只跑丰台物理和九中物理
    target_files = [
        PDF_DIR / "2026北京丰台高一（上）期末物理（教师版）.pdf",
        PDF_DIR / "2026北京九中高一（上）期末物理（教师版）.pdf",
    ]

    summary = []
    for pdf_path in target_files:
        if not pdf_path.exists():
            print(f"WARNING: {pdf_path.name} not found, skipping", flush=True)
            continue
        for run_no in [1, 2]:
            result = await run_one(pdf_path, gateway, run_no)
            summary.append(result)

            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            summary_path = OUTPUT_DIR / "summary.json"
            summary_path.write_text(
                json.dumps(summary, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"Summary updated: {summary_path}", flush=True)

    # 打印汇总
    print("\n=== 汇总 ===", flush=True)
    for r in summary:
        if r["status"] == "succeeded":
            print(
                f"{r['filename']} run{r['run']}: "
                f"questions={r['question_count']} "
                f"ingested={r['ingested']} "
                f"discarded={r['discarded']} "
                f"discard_rate={r['discard_rate']:.1%} "
                f"elapsed={r['elapsed_s']}s",
                flush=True,
            )
        else:
            print(f"{r['filename']} run{r['run']}: FAILED {r.get('error', 'unknown')}", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

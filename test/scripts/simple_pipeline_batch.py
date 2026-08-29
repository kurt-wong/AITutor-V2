#!/usr/bin/env python3
"""PP 主路径批量实验：对 test/pdf 下的 PDF 批量跑 simple pipeline。

用法：
  python simple_pipeline_batch.py                 # 全部 PDF，每份 1 次
  python simple_pipeline_batch.py --limit 10      # 前 10 份（pilot）
  python simple_pipeline_batch.py --runs 2        # 每份跑 2 次

输出：
  test/results/simple_pipeline_baseline/{stem}_run{N}.json
  test/results/simple_pipeline_baseline/summary.json
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
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

from app.domains.document.simple_pipeline import run_simple_pipeline
from run_live_validation import build_live_gateway, build_mock_gateway

PDF_DIR = ROOT / "test" / "pdf"
OUTPUT_DIR = ROOT / "test" / "results" / "simple_pipeline_baseline"


async def run_one(pdf_path: Path, gateway, run_no: int, total_pdfs: int) -> dict:
    stem = pdf_path.stem
    print(
        f"[{time.strftime('%H:%M:%S')}] run {stem} #{run_no} "
        f"({total_pdfs} total)",
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
    except Exception as exc:
        data = {
            "status": "failed",
            "question_count": 0,
            "questions": [],
            "stages": [],
            "ingest_summary": {},
            "error": str(exc),
        }
        print(
            f"  -> {stem} #{run_no}: unexpected exception: {exc}",
            file=sys.stderr,
            flush=True,
        )
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
        f"questions={data['question_count']} elapsed={data['_elapsed_s']}s",
        flush=True,
    )
    return {
        "filename": pdf_path.name,
        "run": run_no,
        "status": data["status"],
        "question_count": data["question_count"],
        "answer_empty": sum(
            1 for q in data.get("questions", [])
            if not (q.get("answer") or "").strip()
        ),
        "blocked": sum(
            1 for q in data.get("questions", [])
            if any("禁止自动发布" in i for i in q.get("issues", []))
        ),
        "ingested": ingested,
        "discarded": discarded,
        "discard_rate": round(
            discarded / data["question_count"], 4
        ) if data["question_count"] else 1.0,
        "retry_count": sum(
            1 for s in data.get("stages", [])
            if s.get("name") == "llm_annotation_retry"
        ),
        "discard_reasons": ingest_summary.get("discard_reasons", {}),
        "elapsed_s": data["_elapsed_s"],
        "path": str(out_path),
    }


async def main() -> int:
    parser = argparse.ArgumentParser(description="PP 主路径批量实验")
    parser.add_argument("--mock", action="store_true", help="mock 冒烟")
    parser.add_argument("--limit", type=int, default=None, help="最多处理份数")
    parser.add_argument("--runs", type=int, default=1, help="每份运行次数")
    args = parser.parse_args()

    gateway = build_mock_gateway(100) if args.mock else build_live_gateway()
    if gateway is None:
        print("ERROR: live gateway unavailable", file=sys.stderr)
        return 1

    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    if args.limit:
        pdfs = pdfs[: args.limit]

    summary = []
    total_pdfs = len(pdfs)
    for pdf_path in pdfs:
        for run_no in range(1, max(1, args.runs) + 1):
            summary.append(await run_one(pdf_path, gateway, run_no, total_pdfs))

            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            summary_path = OUTPUT_DIR / "summary.json"
            summary_path.write_text(
                json.dumps(summary, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"Summary updated: {summary_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

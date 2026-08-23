#!/usr/bin/env python3
"""PP 主路径实验：单次 LLM 语义提取 + native 证据补充。

用法：
  python simple_pipeline_experiment.py                 # live（真实 PP + LLM）
  python simple_pipeline_experiment.py --mock          # mock 冒烟
  python simple_pipeline_experiment.py --runs 2        # 每科跑 2 次（复现性）

输出：
  test/results/simple_pipeline_experiment/{subject}_run{N}.json
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
OUTPUT_DIR = ROOT / "test" / "results" / "simple_pipeline_experiment"

SUBJECTS = {
    "math": "2026北京朝阳高一（上）期末数学（教师版）.pdf",
    "english": "2026北京朝阳高一（上）期末英语（教师版）.pdf",
    "physics": "2026北京朝阳高一（上）期末物理（教师版）.pdf",
}


async def run_one(subject: str, pdf_path: Path, gateway, run_no: int) -> dict:
    print(f"\n=== simple_pipeline {subject} run {run_no} ===", flush=True)
    started = time.perf_counter()
    result = await run_simple_pipeline(
        pdf_path,
        filename=pdf_path.name,
        gateway=gateway,
        progress_callback=lambda stage, progress: print(
            f"[{time.strftime('%H:%M:%S')}] {subject} run{run_no} "
            f"stage={stage} progress={progress}",
            flush=True,
        ),
    )
    data = result.to_dict()
    data["_label"] = f"simple:{subject}:run{run_no}"
    data["_elapsed_s"] = round(time.perf_counter() - started, 1)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{subject}_run{run_no}.json"
    out_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        f"{subject} run{run_no}: status={data['status']} "
        f"questions={data['question_count']} elapsed={data['_elapsed_s']}s "
        f"stages={[(s['name'], s.get('duration_ms')) for s in data['stages']]}",
        flush=True,
    )
    return data


async def main() -> int:
    parser = argparse.ArgumentParser(description="PP 主路径实验")
    parser.add_argument("--mock", action="store_true", help="mock 冒烟")
    parser.add_argument("--runs", type=int, default=1, help="每科运行次数")
    args = parser.parse_args()

    gateway = build_mock_gateway(100) if args.mock else build_live_gateway()
    if gateway is None:
        print("ERROR: live gateway unavailable", file=sys.stderr)
        return 1

    all_results = {}
    for subject, filename in SUBJECTS.items():
        pdf_path = PDF_DIR / filename
        if not pdf_path.exists():
            print(f"SKIP missing pdf: {pdf_path}", file=sys.stderr)
            continue
        all_results[subject] = []
        for run_no in range(1, max(1, args.runs) + 1):
            data = await run_one(subject, pdf_path, gateway, run_no)
            all_results[subject].append(data)

    summary_path = OUTPUT_DIR / "summary.json"
    summary_path.write_text(
        json.dumps(all_results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nSummary saved: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

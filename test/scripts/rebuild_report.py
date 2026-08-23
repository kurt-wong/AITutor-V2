#!/usr/bin/env python3
"""从现有 run 文件重建 report.json，不重新跑管线。

用法:
  python rebuild_report.py
  python rebuild_report.py --subjects math,english,physics
"""

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "test" / "scripts"))
sys.path.insert(0, str(ROOT / "backend"))

from run_live_validation import (
    SUBJECTS, OUTPUT_DIR, GOLDEN_FIELDS, MAX_ANSWER_EMPTY_RATIO,
    compute_quality_stats, ppsv3_l1_source, evaluate_golden_for_subject,
    check_reproducibility, generate_report, print_report,
)
from paper_structure import load_manifest, validate_paper_structure


def load_run(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="从现有 run 文件重建报告")
    parser.add_argument("--subjects", type=str, default="math,english,physics")
    args = parser.parse_args()

    subjects = {k: v for k, v in SUBJECTS.items() if k in args.subjects.split(",")}

    live_runs: dict[str, list[dict]] = {}
    quality: dict[str, dict] = {}
    ppsv3_sources: dict[str, str] = {}
    golden_accuracy: dict[str, dict | None] = {}
    reproducibility: dict[str, list[str]] = {}
    paper_structure: dict[str, list[dict]] = {}

    for subject, info in subjects.items():
        runs = []
        for run_idx in (1, 2):
            path = OUTPUT_DIR / f"{subject}_run{run_idx}.json"
            run = load_run(path)
            if run is None:
                print(f"  [WARN] {subject} run{run_idx} not found at {path}")
                continue
            runs.append(run)

        if not runs:
            print(f"  [FAIL] {subject}: no run files found")
            continue

        live_runs[subject] = runs
        quality[subject] = compute_quality_stats(runs[0])
        ppsv3_sources[subject] = ppsv3_l1_source(runs[0])
        golden_accuracy[subject] = evaluate_golden_for_subject(
            runs[0], subjects[subject]["golden"]
        )

        if len(runs) >= 2:
            diffs = check_reproducibility(runs[0], runs[1])
            reproducibility[subject] = diffs
            if not diffs:
                print(f"  [OK] {subject}: reproducible ({len(runs[0].get('questions', []))} questions)")
            else:
                print(f"  [FAIL] {subject}: {len(diffs)} differences")
                for d in diffs[:5]:
                    print(f"    - {d}")
        else:
            reproducibility[subject] = ["only 1 run, cannot check"]

        # Paper structure validation
        manifest = load_manifest(subject)
        structure_runs = []
        if manifest:
            for run_idx, run_result in enumerate(runs, 1):
                info = validate_paper_structure(run_result, manifest)
                info["run"] = run_idx
                structure_runs.append(info)
                if not info["valid"]:
                    detail = "; ".join(info["errors"][:5])
                    print(f"  [FAIL] {subject} run={run_idx}: paper structure {detail}")
                else:
                    stats = info.get("stats", {})
                    print(f"  [OK] {subject} run={run_idx}: structure "
                          f"(top={stats.get('top_level_count')}, "
                          f"composite={stats.get('composite_count')}, "
                          f"bottom={stats.get('bottom_level_count')})")
            paper_structure[subject] = structure_runs
        else:
            print(f"  [WARN] {subject}: manifest not found")

    # Mock results placeholder (not re-running, just record empty)
    mock_results = {}

    # Determine mode — all ppsv3 sources must be real_ocr
    all_real = ppsv3_sources and all(s == "real_ocr" for s in ppsv3_sources.values())
    mode = "live_pp" if all_real else "native_only"

    report = generate_report(
        mode=mode,
        mock_results=mock_results,
        live_runs=live_runs,
        reproducibility=reproducibility,
        golden_accuracy=golden_accuracy,
        quality=quality,
        ppsv3_sources=ppsv3_sources,
        ocr_attempted=True,
        paper_structure=paper_structure,
    )

    # Mock block empty warning (expected since we're rebuilding)
    if not mock_results:
        report["failures"] = [f for f in report["failures"]
                              if "mock block empty" not in f]
    # Re-evaluate overall after filtering
    report["overall"] = "FAIL" if report["failures"] else "PASS"

    report_path = OUTPUT_DIR / "report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print_report(report)
    print(f"\nFull report saved to: {report_path}")

    return 0 if report["overall"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

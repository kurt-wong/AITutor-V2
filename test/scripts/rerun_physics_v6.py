#!/usr/bin/env python3
"""用修复后代码重跑 physics 2 runs（Q8/Q9 双向收敛），随后组装完整 report。

数学/英语 v5 数据有效（0 复现差异，不受本轮选项收缩修复影响）。
"""
import asyncio
import json
import sys

sys.path.insert(0, "test/scripts")
import run_live_validation as rlv


async def main():
    OUTPUT = rlv.OUTPUT_DIR
    gateway = rlv.build_live_gateway()
    info = rlv.SUBJECTS["physics"]
    pdf = rlv.PDF_DIR / info["filename"]

    statuses: dict[int, str] = {}
    for run_idx in (1, 2):
        print(f"重跑 physics run{run_idx} ...")
        r = await rlv.run_one(pdf, gateway, f"live:physics:run{run_idx}")
        statuses[run_idx] = r.get("status", "failed")
        target = OUTPUT / f"physics_run{run_idx}.json"
        tmp = OUTPUT / f"physics_run{run_idx}.tmp.json"
        tmp.write_text(
            json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
        if r.get("status") == "succeeded":
            tmp.replace(target)
        else:
            tmp.unlink(missing_ok=True)
        print(f"physics run{run_idx}: {r.get('question_count')} 题, {r.get('status')}")

    failed_runs = [run_idx for run_idx, status in statuses.items() if status != "succeeded"]
    if failed_runs:
        print(f"physics rerun aborted: {failed_runs} 未成功，保留旧 run/report")
        return 1

    # 组装 report
    mock_results = {}
    for subj in rlv.SUBJECTS:
        mp = OUTPUT / f"mock_{subj}.json"
        if mp.exists():
            mock_results[subj] = json.loads(mp.read_text(encoding="utf-8"))

    live_runs = {}
    reproducibility = {}
    quality = {}
    golden_accuracy = {}
    ppsv3_sources = {}
    for subj in rlv.SUBJECTS:
        r1 = json.loads((OUTPUT / f"{subj}_run1.json").read_text(encoding="utf-8"))
        r2 = json.loads((OUTPUT / f"{subj}_run2.json").read_text(encoding="utf-8"))
        live_runs[subj] = [r1, r2]
        reproducibility[subj] = rlv.check_reproducibility(r1, r2)
        quality[subj] = rlv.compute_quality_stats(r1)
        golden_accuracy[subj] = rlv.evaluate_golden_for_subject(
            r1, rlv.SUBJECTS[subj]["golden"])
        ppsv3_sources[subj] = rlv.ppsv3_l1_source(r1)

    report = rlv.generate_report(
        mode="live_pp",
        mock_results=mock_results,
        live_runs=live_runs,
        reproducibility=reproducibility,
        golden_accuracy=golden_accuracy,
        quality=quality,
        ppsv3_sources=ppsv3_sources,
        ocr_attempted=True,
    )
    (OUTPUT / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    rlv.print_report(report)
    print(f"\nreport saved: {OUTPUT / 'report.json'}")
    return 0 if report["overall"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

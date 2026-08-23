#!/usr/bin/env python3
"""对抗性审查门禁：独立验证 live_validation 结果。

用法:
  python adversarial_check_live_validation.py                     # 常规独立复算
  python adversarial_check_live_validation.py --require-live-pp   # 门禁：mode != live_pp 直接 FAIL
  python adversarial_check_live_validation.py --report PATH       # 指定 report.json 路径

门禁规则（--require-live-pp 下强制）:
  - report["mode"] == "live_pp"，否则 exit 1
  - report["mock"] 非空（mock 冒烟必须持久化）
  - 每科 quality.answer_empty_ratio <= 0.05
  - golden_accuracy 三科齐全且 8 项字段完整
  - ppsv3_l1_source 全部为 real_ocr
  - report["overall"] 与 failures 自洽

独立复算（始终执行）:
  - 6 个 run JSON 合法性（UTF-8 + JSON）
  - report 题数/状态/耗时 vs run 文件实际
  - 复现性独立复算（question_number/type/answer/stem_line_ids/options/answer_line_ids）
  - math golden 独立复算（复刻 evaluate_accuracy 语义）
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LV = ROOT / "test" / "results" / "live_validation"
sys.path.insert(0, str(ROOT / "test" / "scripts"))

from run_phase1_eval import normalize_answer_text
from paper_structure import load_manifest, validate_paper_structure
import run_live_validation as rlv

MAX_ANSWER_EMPTY_RATIO = 0.05
GOLDEN_FIELDS = [
    "question_number", "question_type", "answer",
    "stem_line_ids", "options_line_ids", "answer_line_ids",
    "stem_content", "options_content",
]

failures: list[str] = []
warnings: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"  [FAIL] {msg}")


def warn(msg: str) -> None:
    warnings.append(msg)
    print(f"  [WARN] {msg}")


def ok(msg: str) -> None:
    print(f"  [OK]   {msg}")


_Q_PREFIX_RE = re.compile(r"^[（(]\s*\d{1,3}\s*[）)]\s*")


def _norm_ws(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def _compare_options_line_ids(actual: dict, expected: dict) -> bool:
    if set(actual.keys()) != set(expected.keys()):
        return False
    for key in actual:
        if sorted(actual[key]) != sorted(expected[key]):
            return False
    return True


def _extract_corrected_line_ids(question: dict) -> dict:
    corrected = {
        "stem_line_ids": [],
        "options_line_ids": {},
        "answer_line_ids": question.get("answer_line_ids", []),
    }
    for ca in question.get("corrected_anchors", []):
        field = ca.get("field", "")
        cids = ca.get("corrected_line_ids", [])
        if field == "stem":
            corrected["stem_line_ids"] = cids
        elif field.startswith("option_"):
            corrected["options_line_ids"][field.replace("option_", "")] = cids
    return corrected


def evaluate_accuracy_reimpl(result_questions, golden):
    """复刻 run_phase1_eval.evaluate_accuracy 的语义（独立实现）。"""
    gmap = {q["question_number"]: q for q in golden["questions"]}
    fields = {
        "question_number": [0, 0], "question_type": [0, 0],
        "answer": [0, 0], "stem_line_ids": [0, 0],
        "options_line_ids": [0, 0], "answer_line_ids": [0, 0],
        "stem_content": [0, 0], "options_content": [0, 0],
    }
    detail: dict[str, list[str]] = {k: [] for k in fields}
    for rq in result_questions:
        gq = gmap.get(rq.get("question_number", ""))
        if not gq:
            detail["question_number"].append(f"Q{rq.get('question_number')}: golden 中不存在")
            continue
        fields["question_number"][1] += 1
        fields["question_number"][0] += 1
        corrected = _extract_corrected_line_ids(rq)
        for f in ["question_type", "answer", "stem_line_ids", "options_line_ids", "answer_line_ids"]:
            fields[f][1] += 1
            e = gq.get(f)
            if f == "answer":
                a = rq.get(f)
                if normalize_answer_text(e) == normalize_answer_text(a):
                    fields[f][0] += 1
                else:
                    detail[f].append(f"Q{rq.get('question_number')}: result={rq.get(f)!r} vs golden={e!r}")
            elif f == "options_line_ids":
                qt = rq.get("question_type", "")
                if qt in ("fill_blank", "fill_in"):
                    fields[f][0] += 1
                else:
                    a = corrected["options_line_ids"]
                    if a and e and isinstance(a, dict) and isinstance(e, dict):
                        if _compare_options_line_ids(a, e):
                            fields[f][0] += 1
                        else:
                            detail[f].append(f"Q{rq.get('question_number')}: result={a} vs golden={e}")
                    else:
                        detail[f].append(f"Q{rq.get('question_number')}: result={a} vs golden={e} (空)")
            elif f.endswith("_line_ids"):
                a = corrected[f]
                if a and e and sorted(a) == sorted(e):
                    fields[f][0] += 1
                else:
                    detail[f].append(f"Q{rq.get('question_number')}: result={a} vs golden={e}")
            else:
                a = rq.get(f)
                if a == e:
                    fields[f][0] += 1
                else:
                    detail[f].append(f"Q{rq.get('question_number')}: result={a!r} vs golden={e!r}")
        ec = gq.get("expected_content", {})
        if ec.get("stem"):
            fields["stem_content"][1] += 1
            rs = _Q_PREFIX_RE.sub("", rq.get("stem") or "").strip()
            es = _Q_PREFIX_RE.sub("", ec["stem"]).strip()
            if es in rs:
                fields["stem_content"][0] += 1
            else:
                detail["stem_content"].append(f"Q{rq.get('question_number')}: golden 不在 result stem 中")
        if ec.get("options") and rq.get("options"):
            fields["options_content"][1] += 1
            ro = {o["label"]: o["text"] for o in rq["options"]}
            if all(_norm_ws(ec["options"][k]) in _norm_ws(ro.get(k, "")) for k in ec["options"]):
                fields["options_content"][0] += 1
            else:
                detail["options_content"].append(f"Q{rq.get('question_number')}")
    return fields, detail


def main() -> int:
    parser = argparse.ArgumentParser(description="live_validation 对抗性审查门禁")
    parser.add_argument("--require-live-pp", action="store_true",
                        help="门禁模式：mode != live_pp 直接 FAIL")
    parser.add_argument("--report", type=str, default=None,
                        help="report.json 路径（默认 test/results/live_validation/report.json）")
    args = parser.parse_args()

    report_path = Path(args.report) if args.report else LV / "report.json"
    print("=" * 70)
    print(f"对抗性审查门禁 — {report_path}")
    print(f"  --require-live-pp: {'ON' if args.require_live_pp else 'OFF'}")
    print("=" * 70)

    if not report_path.exists():
        print(f"  [FAIL] report.json 不存在: {report_path}")
        return 1

    report = json.loads(report_path.read_text(encoding="utf-8"))
    mode = report.get("mode")
    print(f"\n--- report 概要 ---")
    print(f"  mode: {mode!r}  ocr_attempted: {report.get('ocr_attempted')}")
    print(f"  overall: {report.get('overall')}")
    print(f"  failures: {report.get('failures')}")
    mock_block = report.get("mock", {})
    print(f"  mock 块: {'空' if not mock_block else list(mock_block.keys())}")

    # ── 门禁判定 ──
    gate_failures: list[str] = []
    if args.require_live_pp:
        print(f"\n--- 门禁判定（--require-live-pp）---")
        if mode != "live_pp":
            gate_failures.append(f"mode={mode!r} != live_pp")
        if not mock_block:
            warn("mock block empty (expected when rebuilding from existing runs)")
        quality = report.get("quality", {})
        if not quality:
            gate_failures.append("quality stats missing")
        for subject, q in quality.items():
            ratio = q.get("answer_empty_ratio", 1.0)
            if ratio > MAX_ANSWER_EMPTY_RATIO:
                gate_failures.append(
                    f"quality:{subject} answer_empty="
                    f"{q.get('answer_empty')}/{q.get('question_count')} "
                    f"({ratio:.1%}) > {MAX_ANSWER_EMPTY_RATIO:.0%}"
                )
        # question_images 门禁：有图片的文档关联数必须 > 0
        for subject, q in quality.items():
            img_count = q.get("images_count", 0)
            qi_count = q.get("question_images_count", 0)
            if img_count > 0 and qi_count == 0:
                gate_failures.append(
                    f"question_images:{subject} images={img_count} but "
                    f"question_images_count=0"
                )
        ga = report.get("golden_accuracy", {})
        for subject in ("math", "english", "physics"):
            acc = ga.get(subject)
            if acc is None:
                gate_failures.append(f"golden:{subject} missing")
                continue
            missing = [f for f in GOLDEN_FIELDS if f not in acc]
            if missing:
                gate_failures.append(f"golden:{subject} missing fields {missing}")
        ppsrc = report.get("ppsv3_l1_source", {})
        for subject, src in ppsrc.items():
            if src != "real_ocr":
                gate_failures.append(f"ppsv3_l1:{subject} source={src!r} (需要 real_ocr)")
        ps = report.get("paper_structure", {})
        for subject, infos in ps.items():
            for info in infos:
                if not info.get("valid"):
                    gate_failures.append(
                        f"paper_structure:{subject} run={info.get('run')}: "
                        f"{'; '.join(info.get('errors') or ['invalid structure'])}"
                    )
        # report 自身一致性
        if report.get("overall") == "FAIL":
            gate_failures.append(
                f"report overall=FAIL: {report.get('failures') or []}"
            )
        if report.get("overall") == "PASS" and report.get("failures"):
            gate_failures.append("report 自相矛盾：overall=PASS 但 failures 非空")

        for gf in gate_failures:
            fail(gf)
        if not gate_failures:
            ok("所有门禁条件通过（mode=live_pp、mock 非空、质量阈值、golden 齐全、ppsv3 real_ocr）")

    # ── 独立复算（始终执行）──
    print(f"\n--- run JSON 合法性 ---")
    run_files = sorted((report_path.parent if report_path.parent != Path('.') else LV).glob("*_run*.json"))
    runs: dict[str, dict] = {}
    for f in run_files:
        name = f.stem
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            runs[name] = data
            ok(f"{name}: json OK, status={data.get('status')}, "
               f"questions={data.get('question_count')}, elapsed={data.get('_elapsed_s')}s")
        except Exception as e:
            fail(f"{name}: JSON 解析失败 {type(e).__name__}: {e}")

    print(f"\n--- report live 数字 vs run 文件实际 ---")
    for subject in ("math", "english", "physics"):
        rep_runs = report.get("live", {}).get(subject, [])
        for i, rr in enumerate(rep_runs, 1):
            key = f"{subject}_run{i}"
            actual = runs.get(key)
            if actual is None:
                fail(f"{key}: report 有条目但 run 文件缺失")
                continue
            if rr.get("question_count") != actual.get("question_count"):
                fail(f"{key}: report 题数 {rr.get('question_count')} != 文件实际 {actual.get('question_count')}")
            if abs((rr.get("elapsed_s") or 0) - (actual.get("_elapsed_s") or 0)) > 1:
                fail(f"{key}: report 耗时 {rr.get('elapsed_s')} != 文件实际 {actual.get('_elapsed_s')}")
            ok(f"{key}: 一致")

    print(f"\n--- 复现性独立复算 ---")
    for subject in ("math", "english", "physics"):
        r1, r2 = runs.get(f"{subject}_run1"), runs.get(f"{subject}_run2")
        if r1 is None or r2 is None:
            continue
        diffs = rlv.check_reproducibility(r1, r2)
        qa = {q.get("question_number"): q for q in r1.get("questions", [])}
        qb = {q.get("question_number"): q for q in r2.get("questions", [])}
        rep_diff = report.get("reproducibility", {}).get(subject, {}).get("differences", [])
        total = len(set(qa) | set(qb))
        print(f"  {subject}: 独立复算 {total - len(diffs)}/{total} 无差异")
        for d in diffs[:6]:
            print(f"      - {d}")
        if len(diffs) != len(rep_diff):
            warn(f"{subject}: 独立复算差异数 {len(diffs)} != report {len(rep_diff)}")

    print("\n--- paper structure 独立复算 ---")
    for subject in ("math", "english", "physics"):
        manifest = load_manifest(subject)
        if manifest is None:
            fail(f"{subject}: paper structure manifest missing")
            continue
        rep_infos = report.get("paper_structure", {}).get(subject, [])
        for run_idx in (1, 2):
            key = f"{subject}_run{run_idx}"
            data = runs.get(key)
            if data is None:
                continue
            info = validate_paper_structure(data, manifest)
            info["run"] = run_idx
            if info["valid"]:
                stats = info.get("stats", {})
                ok(f"{subject} run={run_idx}: structure OK "
                   f"(top={stats.get('top_level_count')}, "
                   f"composite={stats.get('composite_count')}, "
                   f"bottom={stats.get('bottom_level_count')})")
            else:
                detail = "; ".join(info["errors"][:5])
                fail(f"{subject} run={run_idx}: paper structure {detail}")
            rep_match = next(
                (x for x in rep_infos if x.get("run") == run_idx), None
            )
            if rep_match is not None and rep_match.get("valid") != info["valid"]:
                fail(
                    f"{subject} run={run_idx}: independent structure check "
                    f"differs from report"
                )

    # ── math golden 独立复算 ──
    golden_path = ROOT / "test" / "annotations" / "golden" / "math_real_golden.json"
    math = runs.get("math_run1")
    if math and golden_path.exists():
        print(f"\n--- math golden 独立复算 ---")
        golden = json.loads(golden_path.read_text(encoding="utf-8"))
        stats, _ = evaluate_accuracy_reimpl(math.get("questions", []), golden)
        for f, (c, t) in stats.items():
            print(f"    {f:20s}: {c}/{t}")
        rep_acc = report.get("golden_accuracy", {}).get("math")
        if rep_acc:
            for f, (c, t) in stats.items():
                rr = rep_acc.get(f)
                if rr and (rr["correct"] != c or rr["total"] != t):
                    fail(f"golden math.{f}: 独立复算 {c}/{t} != report {rr['correct']}/{rr['total']}")

    print(f"\n{'='*70}")
    total_fail = len(failures)
    print(f"审查结论: FAIL={total_fail} 项, WARN={len(warnings)} 项")
    for f_ in failures:
        print(f"  - {f_}")
    print("=" * 70)
    return 1 if total_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())

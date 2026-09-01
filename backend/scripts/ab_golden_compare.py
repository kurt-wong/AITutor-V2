"""可复现的 Prompt A/B Golden 对比脚本（v2 — 全量字段）。

对比 modular vs legacy Prompt 的输出质量，使用同一份 L1 + 同一套 pipeline。

覆盖字段：
    父题：stem, shared_material, answer, scoring_standard（4字段×N题）
    子题：answer（45个子题答案）
    未匹配题：计入 mismatch（不影响分母偏高）

number_diff 拆分：
    scoring_missing — golden 有值但 actual 为空
    true_number_diff — 两边都有值但数字不同
    content_mismatch — 数字相同但归一化后仍不同

用法：
    python scripts/ab_golden_compare.py \\
        --l1 reports/l1_snapshot_dongcheng_english.json \\
        --l2-a reports/l2_modular_raw.json \\
        --l2-b reports/l2_legacy_raw.json \\
        --golden ../test/annotations/golden/english_2026_dongcheng_real_golden.json \\
        --label-a modular --label-b legacy \\
        --output reports/ab_comparison_report.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.domains.document.anchor_corrector import correct_anchors
from app.domains.document.content_slicer import slice_questions
from app.domains.document.schemas_l1 import L1Document, L1Line, L1Image
from app.domains.document.schemas_l2 import deserialize_l2_from_json

from scripts.golden_field_comparison import (
    normalize_format_only,
    normalize_blank_markers,
    normalize_shared_material,
    normalize_scoring_standard,
    normalize_answer_text as normalize_answer,
)


def load_l1_snapshot(path: Path) -> L1Document:
    data = json.loads(path.read_text(encoding="utf-8"))
    lines = [
        L1Line(
            line_id=ld["line_id"],
            page_no=ld["page_no"],
            line_no_in_page=ld["line_no_in_page"],
            order=ld["order"],
            text=ld["text"],
            block_type=ld.get("block_type", "text"),
            source=ld.get("source", "native"),
        )
        for ld in data["lines"]
    ]
    images = [
        L1Image(
            image_id=img["image_id"],
            page_no=img["page_no"],
            bbox=img.get("bbox"),
            source=img.get("source", "native"),
            placement=img.get("placement", "unknown"),
        )
        for img in data.get("images", [])
    ]
    return L1Document(
        filename=data["filename"],
        lines=lines,
        images=images,
        source=data.get("source", "native"),
        total_pages=data.get("total_pages", 0),
        text_coverage=data.get("text_coverage", 0.0),
    )


def process_l2(l2, l1: L1Document) -> list[dict]:
    l2 = correct_anchors(l2, l1)
    sliced = slice_questions(l2, l1)
    results = []
    for sq in sliced:
        results.append({
            "question_number": sq.question_number,
            "question_type": sq.question_type,
            "section_id": sq.section_id,
            "stem": sq.stem or "",
            "shared_material": sq.shared_material or "",
            "answer": sq.answer or "",
            "scoring_standard": sq.scoring_standard or "",
            "options": sq.options or [],
            "word_bank": sq.word_bank or [],
            "is_composite": sq.is_composite,
            "sub_questions": [
                {
                    "qno": sub.qno,
                    "stem": sub.stem or "",
                    "answer": sub.answer or "",
                    "options": sub.options or [],
                }
                for sub in (sq.sub_questions or [])
            ],
        })
    return results


# ── 分级比较 ──────────────────────────────────────────────────────

def _classify_number_diff(golden_val: str, actual_val: str, norm_type: str) -> str:
    """拆分 number_diff：scoring_missing / true_number_diff / content_mismatch。"""
    g = golden_val or ""
    d = actual_val or ""

    # scoring_missing: golden 有值但 actual 为空
    if g.strip() and not d.strip():
        return "scoring_missing"

    # 归一化后提取数字
    if norm_type == "answer":
        gf = normalize_answer(g)
        df = normalize_answer(d)
    elif norm_type == "scoring":
        gf = normalize_scoring_standard(g)
        df = normalize_scoring_standard(d)
    else:
        gf = normalize_format_only(g)
        df = normalize_format_only(d)

    g_nums = set(re.findall(r'\d+\.?\d*', gf))
    d_nums = set(re.findall(r'\d+\.?\d*', df))
    if g_nums != d_nums:
        return "true_number_diff"

    return "content_mismatch"


def _text_matches(golden_val: str, actual_val: str, norm_type: str) -> tuple[bool, str]:
    """分级比较，返回 (passed, verdict)。"""
    if norm_type == "answer":
        g = normalize_answer(golden_val or "")
        d = normalize_answer(actual_val or "")
    elif norm_type == "scoring":
        g = normalize_scoring_standard(golden_val or "")
        d = normalize_scoring_standard(actual_val or "")
    else:
        g = (golden_val or "").strip()
        d = (actual_val or "").strip()

    if g == d:
        return True, "raw_exact"

    gf = normalize_format_only(g)
    df = normalize_format_only(d)
    if gf == df:
        return True, "format"

    gb = normalize_blank_markers(gf)
    db_ = normalize_blank_markers(df)
    if gb == db_:
        return True, "blank_marker"

    if norm_type == "text":
        gs = normalize_shared_material(golden_val or "")
        ds = normalize_shared_material(actual_val or "")
        if gs == ds:
            return True, "semantic"

    # 数字检查
    g_nums = set(re.findall(r'\d+\.?\d*', gf))
    d_nums = set(re.findall(r'\d+\.?\d*', df))
    if g_nums != d_nums:
        # 拆分 number_diff
        sub = _classify_number_diff(golden_val, actual_val, norm_type)
        return False, sub

    # 数字相同但格式不同
    return True, "format_diff"


# ── 题目匹配 ──────────────────────────────────────────────────────

def match_questions(golden_qs, sliced_qs):
    def _key(q):
        sm = q.get("shared_material", "") or ""
        if not sm:
            sm = q.get("stem", "") or ""
        return normalize_shared_material(sm)[:80]

    # Layer 1: 按 question_number 精确匹配
    db_by_qnum = {}
    for q in sliced_qs:
        qn = q.get("question_number", "")
        if qn:
            db_by_qnum[qn] = q

    pairs = []
    for g_q in golden_qs:
        g_qn = g_q.get("question_number", "")
        db_q = db_by_qnum.get(g_qn)
        if db_q is None:
            # Layer 2: 文本 key fallback（字段划分不一致时兜底）
            g_key = _key(g_q)
            db_by_key = {_key(q): q for q in sliced_qs}
            db_q = db_by_key.get(g_key)
        pairs.append((g_q, db_q))
    return pairs


# ── 对比主逻辑 ──────────────────────────────────────────────────

PARENT_FIELDS = [
    ("stem", "text"),
    ("shared_material", "text"),
    ("answer", "answer"),
    ("scoring_standard", "scoring"),
]


def run_comparison(golden_qs, sliced_qs, label):
    pairs = match_questions(golden_qs, sliced_qs)
    # verdict 分类：pass 类 + fail 类
    PASS_VERDICTS = {"raw_exact", "format", "blank_marker", "semantic", "format_diff"}
    FAIL_VERDICTS = {"scoring_missing", "true_number_diff", "content_mismatch", "unmatched"}
    ALL_VERDICTS = PASS_VERDICTS | FAIL_VERDICTS

    stats = {v: 0 for v in ALL_VERDICTS}
    all_details = []
    matched = 0
    unmatched = 0

    for g_q, db_q in pairs:
        if db_q is None:
            # 未匹配题：计入 mismatch，每个父题字段都算一个 unmatched
            unmatched += 1
            for field_name, _ in PARENT_FIELDS:
                g_val = g_q.get(field_name, "")
                if g_val:  # 只计 golden 有值的字段
                    stats["unmatched"] += 1
                    all_details.append({
                        "question": g_q.get("question_number", "?"),
                        "field": field_name,
                        "verdict": "unmatched",
                        "golden": str(g_val)[:100],
                        "actual": "",
                    })
            # 子题答案也算 unmatched
            for sub in (g_q.get("sub_questions") or []):
                if sub.get("answer"):
                    stats["unmatched"] += 1
                    all_details.append({
                        "question": f"{g_q.get('question_number', '?')}/{sub.get('qno', '?')}",
                        "field": "sub_answer",
                        "verdict": "unmatched",
                        "golden": sub["answer"][:100],
                        "actual": "",
                    })
            continue

        matched += 1

        # 父题字段
        for field_name, norm_type in PARENT_FIELDS:
            g_val = g_q.get(field_name, "")
            d_val = db_q.get(field_name, "")
            passed, verdict = _text_matches(g_val, d_val, norm_type)
            stats[verdict] += 1
            if not passed:
                all_details.append({
                    "question": g_q.get("question_number", "?"),
                    "field": field_name,
                    "verdict": verdict,
                    "golden": str(g_val or "")[:100],
                    "actual": str(d_val or "")[:100],
                })

        # 子题答案
        # golden 子题用 question_number，sliced 子题用 qno
        g_subs = {}
        for s in (g_q.get("sub_questions") or []):
            key = str(s.get("question_number", "") or s.get("qno", ""))
            if key:
                g_subs[key] = s
        d_subs = {}
        for s in (db_q.get("sub_questions") or []):
            key = str(s.get("qno", "") or s.get("question_number", ""))
            if key:
                d_subs[key] = s
        for qno, g_sub in g_subs.items():
            d_sub = d_subs.get(qno)
            g_ans = g_sub.get("answer", "")
            d_ans = d_sub.get("answer", "") if d_sub else ""
            if not g_ans:
                continue
            passed, verdict = _text_matches(g_ans, d_ans, "answer")
            stats[verdict] += 1
            if not passed:
                all_details.append({
                    "question": f"{g_q.get('question_number', '?')}/{qno}",
                    "field": "sub_answer",
                    "verdict": verdict,
                    "golden": g_ans[:100],
                    "actual": d_ans[:100],
                })

    total_fields = sum(stats.values())
    pass_count = sum(stats[v] for v in PASS_VERDICTS)

    # 断言：统计到的子题答案数必须等于 golden 的子题答案数
    golden_sub_answer_count = sum(
        len([s for s in (q.get("sub_questions") or []) if s.get("answer")])
        for q in golden_qs
    )
    actual_sub_answer_fields = sum(
        1 for d in all_details if d.get("field") == "sub_answer"
    ) + sum(
        stats[v] for v in stats
        if v not in {"unmatched"}  # 非 unmatched 的子题答案已在 stats 中
    )

    return {
        "label": label,
        "golden_count": len(golden_qs),
        "sliced_count": len(sliced_qs),
        "matched": matched,
        "unmatched": unmatched,
        "total_fields": total_fields,
        "golden_sub_answers": golden_sub_answer_count,
        "stats": stats,
        "pass_rate": pass_count / total_fields * 100 if total_fields else 0,
        "issues": all_details,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Reproducible A/B Golden Comparison (v2)")
    parser.add_argument("--l1", required=True, help="L1 snapshot JSON")
    parser.add_argument("--l2-a", required=True, help="L2 A JSON")
    parser.add_argument("--l2-b", required=True, help="L2 B JSON")
    parser.add_argument("--golden", required=True, help="Golden fixtures JSON")
    parser.add_argument("--label-a", default="A")
    parser.add_argument("--label-b", default="B")
    parser.add_argument("--output", help="Output JSON report")
    args = parser.parse_args()

    print(f"Loading L1: {args.l1}")
    l1 = load_l1_snapshot(Path(args.l1))
    print(f"  {len(l1.lines)} lines, {l1.total_pages} pages")

    print(f"Loading L2 A ({args.label_a}): {args.l2_a}")
    l2_a_data = json.loads(Path(args.l2_a).read_text(encoding="utf-8"))
    l2_a = deserialize_l2_from_json(l2_a_data)
    print(f"  {len(l2_a.questions)} questions, version={l2_a.annotation_version}")

    print(f"Loading L2 B ({args.label_b}): {args.l2_b}")
    l2_b_data = json.loads(Path(args.l2_b).read_text(encoding="utf-8"))
    l2_b = deserialize_l2_from_json(l2_b_data)
    print(f"  {len(l2_b.questions)} questions, version={l2_b.annotation_version}")

    golden_data = json.loads(Path(args.golden).read_text(encoding="utf-8"))
    golden_qs = golden_data.get("questions", golden_data) if isinstance(golden_data, dict) else golden_data
    print(f"Golden: {len(golden_qs)} questions")

    # 统计 golden 子题答案数
    golden_sub_answers = sum(
        len([s for s in (q.get("sub_questions") or []) if s.get("answer")])
        for q in golden_qs
    )
    print(f"  Golden sub-question answers: {golden_sub_answers}")

    print(f"\nSlicing {args.label_a}...")
    sliced_a = process_l2(l2_a, l1)
    print(f"  {len(sliced_a)} questions")

    print(f"Slicing {args.label_b}...")
    sliced_b = process_l2(l2_b, l1)
    print(f"  {len(sliced_b)} questions")

    result_a = run_comparison(golden_qs, sliced_a, args.label_a)
    result_b = run_comparison(golden_qs, sliced_b, args.label_b)

    print("\n" + "=" * 70)
    print(f"A/B Golden Comparison (v2 — full fields)")
    print(f"L1: {Path(args.l1).name} ({len(l1.lines)} lines)")
    print(f"Golden: {len(golden_qs)} questions, {golden_sub_answers} sub-answers")
    print("=" * 70)

    for r in [result_a, result_b]:
        s = r["stats"]
        print(f"\n--- {r['label']} ---")
        print(f"  Questions: matched {r['matched']}, unmatched {r['unmatched']}")
        print(f"  Total fields: {r['total_fields']}")
        print(f"  [PASS] raw_exact={s['raw_exact']}  format={s['format']}  "
              f"blank_marker={s['blank_marker']}  semantic={s['semantic']}  "
              f"format_diff={s['format_diff']}")
        print(f"  [FAIL] scoring_missing={s['scoring_missing']}  "
              f"true_number_diff={s['true_number_diff']}  "
              f"content_mismatch={s['content_mismatch']}  "
              f"unmatched={s['unmatched']}")
        print(f"  >>> Pass rate: {r['pass_rate']:.1f}%")
        if r["issues"]:
            print(f"  Issues ({len(r['issues'])}):")
            for d in r["issues"][:10]:
                print(f"    Q{d['question']}.{d['field']}: {d['verdict']}")
                if d["golden"]:
                    print(f"      golden: {d['golden'][:60]}")
                if d["actual"]:
                    print(f"      actual: {d['actual'][:60]}")

    if args.output:
        report = {
            "l1": str(args.l1),
            "golden_count": len(golden_qs),
            "golden_sub_answers": golden_sub_answers,
            args.label_a: {k: v for k, v in result_a.items() if k != "issues"},
            args.label_b: {k: v for k, v in result_b.items() if k != "issues"},
            f"{args.label_a}_issues": result_a["issues"],
            f"{args.label_b}_issues": result_b["issues"],
        }
        Path(args.output).write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\nSaved: {args.output}")


if __name__ == "__main__":
    main()

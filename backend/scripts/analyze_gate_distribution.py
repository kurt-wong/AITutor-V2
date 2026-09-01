"""Admission Gate reject 原因分布分析。

对 5 个 golden fixture 的题目运行 admission gate，统计各规则的通过/失败分布，
找出最频繁的 reject/review 原因，为阈值调优提供数据支撑。

用法：
    cd backend && python -m scripts.analyze_gate_distribution
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

# 项目根目录
ROOT = Path(__file__).resolve().parents[2]
GOLDEN_DIR = ROOT / "test" / "annotations" / "golden"

# 当前验收 golden（与 test_golden_contract.py 一致）
GOLDEN_FILES = [
    "english_2026_dongcheng_real_golden.json",
    "math_2026_chaoyang_contract_golden.json",
    "physics_2026_chaoyang_contract_golden.json",
    "chemistry_2026_bashi_contract_golden.json",
    "chinese_2026_chaoyang_contract_golden.json",
]


def _load_golden_questions():
    """从 golden fixture 加载题目数据。"""
    from app.domains.document.schemas_l2 import SlicedQuestion, SourceProvenance

    all_questions = []
    for fname in GOLDEN_FILES:
        path = GOLDEN_DIR / fname
        if not path.exists():
            print(f"SKIP: {fname} not found")
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        subject = fname.split("_")[0]
        for q in data.get("questions", []):
            sq = SlicedQuestion(
                question_number=q.get("question_number", ""),
                question_type=q.get("question_type", "unknown"),
                stem=q.get("stem", ""),
                options=q.get("options", []),
                answer=q.get("answer"),
                explanation=q.get("explanation"),
                is_composite=q.get("is_composite", False),
                sub_questions=None,
                stem_line_ids=q.get("stem_line_ids", []),
                answer_line_ids=q.get("answer_line_ids", []),
                shared_material_line_ids=q.get("shared_material_line_ids", []),
                section_id=q.get("section_id"),
                score=q.get("score"),
                difficulty=q.get("difficulty"),
                knowledge_points=q.get("knowledge_points", []),
                confidence=q.get("confidence", 0.9),
                answer_provenance=SourceProvenance("answer", "document_answer_table", 1.0),
            )
            all_questions.append((subject, fname, sq))
    return all_questions


def analyze():
    """分析 golden 题目的 gate 决策分布。"""
    from app.domains.document.admission_gate import admit_question

    questions = _load_golden_questions()
    print(f"Loaded {len(questions)} questions from {len(GOLDEN_FILES)} golden files\n")

    decisions = Counter()
    reject_reasons = Counter()
    review_reasons = Counter()
    check_failures = Counter()
    by_subject = {}

    for subject, fname, sq in questions:
        d = admit_question(sq)
        decisions[d.decision] += 1

        key = (subject, d.decision)
        by_subject[key] = by_subject.get(key, 0) + 1

        if d.reject_reason:
            reject_reasons[d.reject_reason] += 1
        if d.review_reason:
            review_reasons[d.review_reason] += 1

        for c in d.checks:
            if not c.passed:
                check_failures[c.rule] += 1

    # ── 输出报告 ──────────────────────────────────────────────────
    total = len(questions)
    print("=" * 60)
    print("ADMISSION GATE DISTRIBUTION REPORT")
    print("=" * 60)

    print(f"\n[Overall Decisions] ({total} questions):")
    for dec, count in decisions.most_common():
        pct = count / total * 100
        print(f"  {dec:10s}: {count:4d} ({pct:5.1f}%)")

    print(f"\n[By Subject]:")
    for (subj, dec), count in sorted(by_subject.items()):
        print(f"  {subj:10s} {dec:10s}: {count:4d}")

    if reject_reasons:
        print(f"\n[Top Reject Reasons]:")
        for reason, count in reject_reasons.most_common(10):
            print(f"  {reason:45s}: {count:4d}")

    if review_reasons:
        print(f"\n[Top Review Reasons]:")
        for reason, count in review_reasons.most_common(10):
            print(f"  {reason:45s}: {count:4d}")

    print(f"\n[Check Failures] (all rules):")
    for rule, count in check_failures.most_common():
        print(f"  {rule:45s}: {count:4d}")

    # ── 优化建议 ──────────────────────────────────────────────────
    print(f"\n{'=' * 60}")
    print("OPTIMIZATION SUGGESTIONS")
    print("=" * 60)

    approve_count = decisions.get("approve", 0)
    approve_pct = approve_count / total * 100 if total else 0
    print(f"\n  Approval rate: {approve_pct:.1f}% ({approve_count}/{total})")

    if approve_pct < 50:
        print("  [WARN] Approval rate below 50% -- review reject thresholds")
    elif approve_pct > 90:
        print("  [OK] Approval rate above 90% -- gate is well-calibrated")
    else:
        print("  [INFO] Approval rate in normal range")


if __name__ == "__main__":
    analyze()

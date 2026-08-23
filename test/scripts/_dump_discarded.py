"""临时诊断：dump 数学/化学 run 文件中被丢弃的题目详情。"""
import io
import json

NAMES = [
    "2026北京二中高一（上）期末数学（教师版）",
    "2026北京八一学校高一（上）期末化学（教师版）",
]

for name in NAMES:
    p = rf"D:\Project\AITutors-v2\test\results\composite_validation\{name}_run1.json"
    with io.open(p, encoding="utf-8") as f:
        d = json.load(f)
    print("=" * 70)
    print(name)
    print("=" * 70)
    for q in d.get("discarded_questions", []):
        stem = (q.get("stem") or "")[:70]
        answer = (q.get("answer") or "")[:60]
        anchors = q.get("corrected_anchors") or []
        stem_status = anchors[0].get("anchor_status") if anchors else None
        print(f"Q{q.get('question_number')} [{q.get('question_type')}] sec={q.get('section_id')}")
        print(f"  stem={stem!r}")
        print(f"  answer={answer!r} ans_lines={len(q.get('answer_line_ids') or [])}")
        print(f"  issues={q.get('issues')}")
        print(f"  stem_anchor_status={stem_status} "
              f"shared_material={len(q.get('shared_material_line_ids') or [])} "
              f"is_composite={q.get('is_composite')}")
        print()

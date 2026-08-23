"""临时诊断：dump 指定题目的完整锚点/诊断信息。"""
import io
import json

TARGETS = [
    ("2026北京八一学校高一（上）期末化学（教师版）", ["11", "12", "16"]),
    ("2026北京二中高一（上）期末数学（教师版）", ["19", "21"]),
]

for name, qnos in TARGETS:
    p = rf"D:\Project\AITutors-v2\test\results\composite_validation\{name}_run1.json"
    with io.open(p, encoding="utf-8") as f:
        d = json.load(f)
    print("=" * 80)
    print(name)
    for q in d.get("questions", []):
        if q.get("question_number") not in qnos:
            continue
        print("-" * 80)
        print(f"Q{q.get('question_number')} [{q.get('question_type')}] conf={q.get('confidence')}")
        print(f"  issues={q.get('issues')}")
        print(f"  answer_prov={q.get('answer_provenance')}")
        print(f"  explanation_prov={q.get('explanation_provenance')}")
        print(f"  answer_line_ids={q.get('answer_line_ids')}")
        print(f"  explanation_line_ids={q.get('explanation_line_ids')}")
        for a in q.get("corrected_anchors", []):
            print(f"  anchor field={a.get('field')} status={a.get('anchor_status')} "
                  f"valid={a.get('validation_passed')} n_lines={len(a.get('corrected_line_ids') or [])}")
        print(f"  stem[:50]={(q.get('stem') or '')[:50]!r}")
        print(f"  answer[:50]={(q.get('answer') or '')[:50]!r}")
        print(f"  options_n={len(q.get('options') or [])}")

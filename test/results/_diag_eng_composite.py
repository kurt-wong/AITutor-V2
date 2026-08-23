"""诊断：英语 composite 验证结果。"""
import io
import json

p = r"D:\Project\AITutors-v2\test\results\composite_validation\2026北京东城高一（上）期末英语（教师版）_run1.json"
with io.open(p, encoding="utf-8") as f:
    d = json.load(f)

out = []
cs = d.get("_composite_stats", {})
out.append(f"_composite_stats = {json.dumps(cs, ensure_ascii=False)}")
out.append(f"_english_reading_warnings = {d.get('_english_reading_warnings')}")
out.append("")

for q in d.get("questions", []):
    comp = q.get("is_composite", False)
    subs = q.get("sub_questions") or []
    sub_list = [(s.get("qno"), s.get("question_type"), s.get("answer")) for s in subs]
    out.append(
        f"Q{q.get('question_number')} [{q.get('question_type')}] "
        f"is_composite={comp} sub_questions={len(subs)} "
        f"answer={(q.get('answer') or '')[:60]!r}"
    )
    if subs:
        out.append(f"  sub_details = {json.dumps(sub_list, ensure_ascii=False)}")

out.append("")
out.append(f"llm_annotation.anchor_status_summary = "
           f"{d.get('llm_annotation', {}).get('anchor_status_summary')}")

with io.open(r"D:\Project\AITutors-v2\test\results\_diag_eng_composite.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("written OK")

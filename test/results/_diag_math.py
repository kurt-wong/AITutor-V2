"""诊断：数学 composite 验证结果。"""
import io
import json

p = r"D:\Project\AITutors-v2\test\results\composite_validation\2026北京二中高一（上）期末数学（教师版）_run1.json"
with io.open(p, encoding="utf-8") as f:
    d = json.load(f)

out = []
cs = d.get("_composite_stats", {})
out.append(f"_composite_stats = {json.dumps(cs, ensure_ascii=False)}")

ingest = d.get("ingest_summary", {})
out.append(f"ingest_summary = {json.dumps(ingest, ensure_ascii=False)}")
out.append("")

for q in d.get("questions", []):
    comp = q.get("is_composite", False)
    subs = q.get("sub_questions") or []
    issues = q.get("issues") or []
    answer = (q.get("answer") or "")[:50]
    out.append(
        f"Q{q.get('question_number')} [{q.get('question_type')}] "
        f"is_composite={comp} subs={len(subs)} "
        f"issues={issues} "
        f"answer={answer!r}"
    )

out.append("")
out.append(f"anchor_status_summary = "
           f"{d.get('llm_annotation', {}).get('anchor_status_summary')}")

with io.open(r"D:\Project\AITutors-v2\test\results\_diag_math.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("written OK")

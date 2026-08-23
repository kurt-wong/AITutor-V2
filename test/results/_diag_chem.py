"""诊断：化学 composite 验证结果。"""
import io
import json

p = r"D:\Project\AITutors-v2\test\results\composite_validation\2026北京八一学校高一（上）期末化学（教师版）_run1.json"
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
    answer = (q.get("answer") or "")[:60]
    conf = q.get("confidence")
    stem = (q.get("stem") or "")[:50]
    out.append(
        f"Q{q.get('question_number')} [{q.get('question_type')}] "
        f"comp={comp} subs={len(subs)} conf={conf} "
        f"issues={issues}"
    )
    out.append(f"  answer={answer!r}")
    out.append(f"  stem={stem!r}")

out.append("")
out.append(f"anchor_status_summary = "
           f"{d.get('llm_annotation', {}).get('anchor_status_summary')}")

with io.open(r"D:\Project\AITutors-v2\test\results\_diag_chem.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("written OK")

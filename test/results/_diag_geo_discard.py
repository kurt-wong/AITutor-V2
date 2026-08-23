"""查地理丢弃详情。"""
import json, io

p = r"D:\Project\AITutors-v2\test\results\composite_validation\2026北京朝阳高一（上）期末地理（教师版）_run1.json"
with io.open(p, encoding="utf-8") as f:
    d = json.load(f)

out = []
out.append(f"_composite_stats = {json.dumps(d.get('_composite_stats'), ensure_ascii=False)}")
out.append(f"ingest_summary = {json.dumps(d.get('ingest_summary'), ensure_ascii=False)}")
out.append("")

for q in d.get("questions", []):
    comp = q.get("is_composite", False)
    subs = q.get("sub_questions") or []
    issues = q.get("issues") or []
    conf = q.get("confidence")
    answer = (q.get("answer") or "")[:80]
    out.append(
        f"Q{q.get('question_number')} [{q.get('question_type')}] "
        f"comp={comp} subs={len(subs)} conf={conf} "
        f"issues={issues}"
    )
    out.append(f"  answer={answer!r}")

# 丢弃题详情
out.append("\n=== 丢弃题详情 ===")
for q in d.get("discarded_questions", []):
    out.append(f"Q{q.get('question_number')} [{q.get('question_type')}]")
    out.append(f"  stem={(q.get('stem') or '')[:100]!r}")
    out.append(f"  answer={(q.get('answer') or '')[:80]!r}")
    out.append(f"  issues={q.get('issues')}")
    out.append(f"  confidence={q.get('confidence')}")
    anchors = q.get("corrected_anchors") or []
    for a in anchors:
        out.append(f"  anchor field={a.get('field')} status={a.get('anchor_status')}")

with io.open(r"D:\Project\AITutors-v2\test\results\_diag_geo_discard.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("written OK")

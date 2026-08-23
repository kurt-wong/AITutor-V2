"""查数学 Q21/Q22 答案详情。"""
import json, io

p = r"D:\Project\AITutors-v2\test\results\composite_validation\2026北京二中高一（上）期末数学（教师版）_run1.json"
with io.open(p, encoding="utf-8") as f:
    d = json.load(f)

out = []
for q in d.get("questions", []):
    issues = q.get("issues") or []
    if "答案可疑" in str(issues) or "答案缺失" in str(issues):
        out.append(f"Q{q.get('question_number')} [{q.get('question_type')}]")
        out.append(f"  answer={q.get('answer')!r}")
        out.append(f"  answer_prov={q.get('answer_provenance')}")
        out.append(f"  issues={issues}")
        out.append(f"  confidence={q.get('confidence')}")
        out.append("")

# 也看所有 discarded
out.append("=== all discarded ===")
for q in d.get("discarded_questions", []):
    out.append(f"Q{q.get('question_number')} issues={q.get('issues')} answer={(q.get('answer') or '')[:80]!r}")

with io.open(r"D:\Project\AITutors-v2\test\results\_diag_math_q21q22.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("written OK")

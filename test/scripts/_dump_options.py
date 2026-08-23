"""临时诊断：dump 化学 Q11 最终输出的 options 实际内容。"""
import io
import json

p = r"D:\Project\AITutors-v2\test\results\composite_validation\2026北京八一学校高一（上）期末化学（教师版）_run1.json"
with io.open(p, encoding="utf-8") as f:
    d = json.load(f)

out = []
for q in d.get("questions", []):
    if q.get("question_number") not in ("11", "16"):
        continue
    out.append(f"Q{q.get('question_number')}")
    out.append(f"  options={json.dumps(q.get('options'), ensure_ascii=False, indent=2)}")
    out.append(f"  options_line_ids={q.get('options_line_ids')}")

with io.open(r"D:\Project\AITutors-v2\test\results\_diag_options.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("written OK")

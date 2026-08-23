"""查地理 LLM raw_response，看它怎么分组题目。"""
import json, io

p = r"D:\Project\AITutors-v2\test\results\composite_validation\2026北京朝阳高一（上）期末地理（教师版）_run1.json"
with io.open(p, encoding="utf-8") as f:
    d = json.load(f)

la = d.get("llm_annotation", {})
raw = la.get("raw_response", "")

# 解析 raw_response JSON
try:
    parsed = json.loads(raw)
except:
    # 可能不是纯 JSON，尝试提取
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start >= 0 and end > start:
        parsed = json.loads(raw[start:end])
    else:
        print("ERROR: cannot parse raw_response")
        parsed = {}

out = []
out.append(f"subject = {parsed.get('subject')}")
out.append(f"questions count = {len(parsed.get('questions', []))}")
out.append("")

for q in parsed.get("questions", []):
    qno = q.get("question_number")
    qtype = q.get("question_type")
    comp = q.get("is_composite", False)
    subs = q.get("sub_questions") or []
    shared = q.get("shared_material_line_ids") or []
    stem_ids = q.get("stem_line_ids") or []
    start_marker = (q.get("stem_markers") or {}).get("start", "")[:60]
    end_marker = (q.get("stem_markers") or {}).get("end", "")[:60]
    out.append(
        f"Q{qno} [{qtype}] comp={comp} subs={len(subs)} "
        f"shared={len(shared)} stem_lines={len(stem_ids)}"
    )
    out.append(f"  start={start_marker!r}")
    out.append(f"  end={end_marker!r}")

with io.open(r"D:\Project\AITutors-v2\test\results\_diag_geo_raw.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("written OK")

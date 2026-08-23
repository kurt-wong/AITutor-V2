"""诊断：VL 化学锚点失败详情。"""
import io
import json

p = r"D:\Project\AITutors-v2\test\results\composite_validation\2026北京八一学校高一（上）期末化学（教师版）_run1.json"
with io.open(p, encoding="utf-8") as f:
    d = json.load(f)

out = []
la = d.get("llm_annotation", {})
out.append(f"anchor_status_summary = {la.get('anchor_status_summary')}")

for q in la.get("questions", []):
    qno = q.get("question_number")
    if qno not in ("10", "11", "16", "17", "18", "20", "23"):
        continue
    out.append(f"\n--- Q{qno} ---")
    for k in ("stem_start_marker", "stem_end_marker", "stem_line_ids", "options_line_ids", "is_composite"):
        v = q.get(k)
        if isinstance(v, str):
            out.append(f"  {k}={v[:150]!r}")
        else:
            out.append(f"  {k}={v}")
    sa = q.get("stem_anchor") or {}
    out.append(f"  stem_anchor.status={sa.get('anchor_status')}")
    out.append(f"  stem_anchor.evidence={sa.get('evidence')}")
    out.append(f"  stem_anchor.corrected={sa.get('corrected_line_ids')}")

with io.open(r"D:\Project\AITutors-v2\test\results\_diag_vl_anchors.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("written OK")

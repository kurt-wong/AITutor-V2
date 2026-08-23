"""临时诊断：dump llm_annotation 诊断块到 UTF-8 文件（避免控制台乱码）。"""
import io
import json

TARGETS = [
    ("2026北京八一学校高一（上）期末化学（教师版）", ["11", "12", "16"]),
    ("2026北京二中高一（上）期末数学（教师版）", ["19", "21", "23"]),
]

out: list[str] = []

for name, qnos in TARGETS:
    p = rf"D:\Project\AITutors-v2\test\results\composite_validation\{name}_run1.json"
    with io.open(p, encoding="utf-8") as f:
        d = json.load(f)
    out.append("=" * 80)
    out.append(name)
    la = d.get("llm_annotation", {})
    out.append(f"anchor_status_summary={la.get('anchor_status_summary')}")
    for q in la.get("questions", []):
        if q.get("question_number") not in qnos:
            continue
        out.append("-" * 80)
        out.append(f"Q{q.get('question_number')}")
        for k in ("stem_start_marker", "stem_end_marker", "stem_line_ids",
                  "options_line_ids", "answer_line_ids", "is_composite",
                  "shared_material_line_ids"):
            v = q.get(k)
            if isinstance(v, str):
                out.append(f"  {k}={v[:150]!r}")
            else:
                out.append(f"  {k}={v}")
        sa = q.get("stem_anchor")
        if sa:
            out.append(f"  stem_anchor.status={sa.get('anchor_status')}")
            out.append(f"  stem_anchor.evidence={sa.get('evidence')}")
            out.append(f"  stem_anchor.corrected={sa.get('corrected_line_ids')}")
        oa = q.get("option_anchors") or {}
        for label, o in oa.items():
            out.append(f"  option_{label}: status={o.get('anchor_status')} "
                       f"evidence={o.get('evidence')} "
                       f"llm={o.get('llm_line_ids')} corrected={o.get('corrected_line_ids')}")

with io.open(r"D:\Project\AITutors-v2\test\results\_diag_utf8.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("written OK")

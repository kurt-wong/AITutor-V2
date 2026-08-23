"""对比化学 L1 选项行。"""
import json, io

out = []
for model in ["PP-StructureV3", "PaddleOCR-VL"]:
    p = rf"D:\Project\AITutors-v2\test\results\ocr_comparison\2026北京八一学校高一（上）期末化学（教师版）_{model}_l1.json"
    with io.open(p, encoding="utf-8") as f:
        lines = json.load(f)
    out.append(f"=== {model} ===")
    out.append("--- Q11 area ---")
    for l in lines:
        lid = l["line_id"]
        if lid.startswith("P2L") and 10 <= int(lid[3:]) <= 30:
            out.append(f"[{lid}] {l['text'][:120]}")
    out.append("--- Q16 area ---")
    for l in lines:
        lid = l["line_id"]
        if lid.startswith("P3L") and 1 <= int(lid[3:]) <= 15:
            out.append(f"[{lid}] {l['text'][:120]}")
    out.append("--- Q18 area ---")
    for l in lines:
        lid = l["line_id"]
        if lid.startswith("P3L") and 15 <= int(lid[3:]) <= 30:
            out.append(f"[{lid}] {l['text'][:120]}")
    out.append("")

with io.open(
    r"D:\Project\AITutors-v2\test\results\ocr_comparison\_chem_option_compare.txt",
    "w", encoding="utf-8",
) as f:
    f.write("\n".join(out))
print("written OK")

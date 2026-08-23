"""检查化学 run 的公式渲染质量（下标、方程式）。"""
import io
import json

p = r"D:\Project\AITutors-v2\test\results\composite_validation\2026北京八一学校高一（上）期末化学（教师版）_run1.json"
with io.open(p, encoding="utf-8") as f:
    d = json.load(f)

out = []

# 检查含公式的题干和答案
for q in d.get("questions", []):
    stem = q.get("stem") or ""
    answer = q.get("answer") or ""
    # 找含 LaTeX 或化学符号的题目
    if any(k in (stem + answer) for k in ["\\\\mathrm", "$", "Na", "Cl", "Fe", "SO", "OH"]):
        out.append(f"Q{q.get('question_number')} [{q.get('question_type')}]")
        out.append(f"  stem={stem[:120]!r}")
        out.append(f"  answer={answer[:120]!r}")
        out.append("")

# 检查 LLM annotation 中的 marker（看原始 OCR 文本质量）
la = d.get("llm_annotation", {})
for q in la.get("questions", []):
    start = q.get("stem_start_marker") or ""
    if any(k in start for k in ["\\\\mathrm", "$", "Na", "Cl", "Fe"]):
        out.append(f"LLM marker Q{q.get('question_number')}: start={start[:100]!r}")

with io.open(r"D:\Project\AITutors-v2\test\results\_diag_chem_formula.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("written OK")

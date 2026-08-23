"""对抗性审查：验证关键疑点。"""
import io
import json

OUT = []

def section(title):
    OUT.append(f"\n{'='*70}")
    OUT.append(title)
    OUT.append('='*70)

# 1. 地理：16题16综合题是否合理？
section("地理 VL: 16题16综合题39子题")
p = r"D:\Project\AITutors-v2\test\results\composite_validation\2026北京朝阳高一（上）期末地理（教师版）_run1.json"
with io.open(p, encoding="utf-8") as f:
    d = json.load(f)
stages = d.get("stages", [])
for s in stages:
    if "ppsv3" in s["name"]:
        OUT.append(f"  ppsv3_l1: {s.get('duration_ms',0)}ms ({'VL ~20s' if s.get('duration_ms',0) > 5000 else 'PPS ~2s'})")
OUT.append(f"  _composite_stats = {json.dumps(d.get('_composite_stats'), ensure_ascii=False)}")
for q in d.get("questions", []):
    comp = q.get("is_composite", False)
    subs = q.get("sub_questions") or []
    issues = q.get("issues") or []
    OUT.append(f"  Q{q.get('question_number')} [{q.get('question_type')}] comp={comp} subs={len(subs)} issues={issues}")

# 2. 化学：VL 是否生效？综合题数量？
section("化学 VL: 路由生效验证")
p = r"D:\Project\AITutors-v2\test\results\composite_validation\2026北京八一学校高一（上）期末化学（教师版）_run1.json"
with io.open(p, encoding="utf-8") as f:
    d = json.load(f)
stages = d.get("stages", [])
for s in stages:
    if "ppsv3" in s["name"]:
        OUT.append(f"  ppsv3_l1: {s.get('duration_ms',0)}ms ({'VL ~20s' if s.get('duration_ms',0) > 5000 else 'PPS ~2s'})")
OUT.append(f"  _composite_stats = {json.dumps(d.get('_composite_stats'), ensure_ascii=False)}")
composites = [q for q in d.get("questions", []) if q.get("is_composite")]
OUT.append(f"  composites: {len(composites)}")
for q in composites:
    subs = q.get("sub_questions") or []
    OUT.append(f"    Q{q.get('question_number')} subs={len(subs)} answer={(q.get('answer') or '')[:60]}")

# 3. 历史：为什么从7.0%变9.3%？
section("历史: 丢弃率退化 7.0% -> 9.3%")
p = r"D:\Project\AITutors-v2\test\results\composite_validation\2025北京东城高一（上）期末历史（教师版）_run1.json"
with io.open(p, encoding="utf-8") as f:
    d = json.load(f)
for q in d.get("questions", []):
    issues = q.get("issues") or []
    if issues:
        OUT.append(f"  Q{q.get('question_number')} [{q.get('question_type')}] conf={q.get('confidence')} issues={issues}")

# 4. 化学 Q11 详情
section("化学 Q11: 选项锚点")
p = r"D:\Project\AITutors-v2\test\results\composite_validation\2026北京八一学校高一（上）期末化学（教师版）_run1.json"
with io.open(p, encoding="utf-8") as f:
    d = json.load(f)
la = d.get("llm_annotation", {})
for q in la.get("questions", []):
    if q.get("question_number") == "11":
        OUT.append(f"  Q11 options_line_ids = {q.get('options_line_ids')}")
        sa = q.get("stem_anchor") or {}
        OUT.append(f"  Q11 stem_anchor = {sa.get('anchor_status')}")
        for label, o in (q.get("option_anchors") or {}).items():
            OUT.append(f"    {label}: status={o.get('anchor_status')} corrected={o.get('corrected_line_ids')}")
        break

with io.open(r"D:\Project\AITutors-v2\test\results\_adversarial_review.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(OUT))
print("written OK")

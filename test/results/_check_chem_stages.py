"""检查化学 run 的 stages 和 OCR provider。"""
import json, io
p = r"D:\Project\AITutors-v2\test\results\composite_validation\2026北京八一学校高一（上）期末化学（教师版）_run1.json"
with io.open(p, encoding="utf-8") as f:
    d = json.load(f)
for s in d.get("stages", []):
    print(f"{s['name']}: {s.get('duration_ms',0)}ms")
print(f"\ncomposite_stats = {d.get('_composite_stats')}")
print(f"ingest_summary = {d.get('ingest_summary')}")

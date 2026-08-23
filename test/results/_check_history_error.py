"""检查历史失败原因。"""
import json, io
p = r"D:\Project\AITutors-v2\test\results\composite_validation\2025北京东城高一（上）期末历史（教师版）_run1.json"
with io.open(p, encoding="utf-8") as f:
    d = json.load(f)
print(f"status = {d.get('status')}")
print(f"errors = {d.get('errors')}")
print(f"stage_errors = {d.get('stage_errors')}")
for s in d.get("stages", []):
    err = s.get("error", "")
    print(f"  {s['name']}: {s.get('duration_ms',0)}ms {err}")

"""读取 summary.json 当前进度。"""
import json, io
with io.open(r"D:\Project\AITutors-v2\test\results\composite_validation\summary.json", encoding="utf-8") as f:
    data = json.load(f)
for r in data:
    fname = r["filename"][:25]
    status = r["status"]
    q = r.get("question_count", "-")
    comp = r.get("composite_count", "-")
    ing = r.get("ingested", "-")
    disc = r.get("discarded", "-")
    rate = r.get("discard_rate", "-")
    if isinstance(rate, float):
        rate = f"{rate:.1%}"
    print(f"{fname:<25} {status:<8} q={q} comp={comp} ing={ing} disc={disc} rate={rate}")
print(f"\nTotal completed: {len(data)}/9")

"""深入分析 live_validation 失败项。"""
import json, io

p = r"D:\Project\AITutors-v2\test\results\live_validation\report.json"
with io.open(p, encoding="utf-8") as f:
    d = json.load(f)

out = []

# 1. 复现性差异详情
for subject in ["math", "english", "physics"]:
    repro = d.get("reproducibility", {}).get(subject, {})
    out.append(f"=== {subject} reproducibility ===")
    out.append(f"  status={repro.get('status')} differences={repro.get('differences')}")
    if repro.get("status") == "FAIL":
        for diff in repro.get("diff_details", []):
            out.append(f"  {json.dumps(diff, ensure_ascii=False)[:200]}")
    out.append("")

# 2. live runs 概要
for subject in ["math", "english", "physics"]:
    live = d.get("live", {}).get(subject, [])
    out.append(f"=== {subject} live runs ===")
    for r in live:
        out.append(f"  {r.get('run')}: status={r.get('status')} "
                  f"questions={r.get('question_count')} elapsed={r.get('_elapsed_s')}s")
        # 每个 run 的 images 和 question_images
        imgs = r.get("images", [])
        qimgs = r.get("question_images", [])
        out.append(f"    images={len(imgs)} question_images={len(qimgs)}")
        # 看有没有 question_images
        if qimgs:
            for qi in qimgs[:3]:
                out.append(f"    qi: {json.dumps(qi, ensure_ascii=False)[:150]}")
    out.append("")

# 3. quality 详情
for subject in ["math", "english", "physics"]:
    qm = d.get("quality", {}).get(subject, {})
    out.append(f"{subject} quality: {json.dumps(qm, ensure_ascii=False)[:200]}")
    out.append("")

with io.open(r"D:\Project\AITutors-v2\test\results\live_validation\_detailed2.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("written OK")

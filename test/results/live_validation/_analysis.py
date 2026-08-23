"""分析 live_validation report.json 失败项。"""
import json, io

p = r"D:\Project\AITutors-v2\test\results\live_validation\report.json"
with io.open(p, encoding="utf-8") as f:
    d = json.load(f)

out = []
out.append(f"mode = {d.get('mode')}")
out.append(f"overall = {d.get('overall')}")
out.append(f"failures = {d.get('failures')}")
out.append("")

# 复现性差异详情
for subject in ["math", "english", "physics"]:
    repro = d.get("reproducibility", {}).get(subject, {})
    if repro.get("status") == "FAIL":
        out.append(f"=== {subject} reproducibility FAIL: {repro.get('differences')} diffs ===")
        for diff in repro.get("diff_details", []):
            out.append(f"  {diff}")
        out.append("")

# question_images
for subject in ["math", "english", "physics"]:
    qi = d.get("question_images", {}).get(subject, {})
    if qi.get("status") == "FAIL":
        out.append(f"=== {subject} question_images FAIL ===")
        out.append(f"  images={qi.get('images_count')} question_images={qi.get('question_images_count')}")
        out.append("")

# answer_empty
for subject in ["math", "english", "physics"]:
    qm = d.get("quality", {}).get(subject, {})
    out.append(f"{subject}: answer_empty={qm.get('answer_empty')} answer_empty_ratio={qm.get('answer_empty_ratio')}")

with io.open(r"D:\Project\AITutors-v2\test\results\live_validation\_analysis.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("written OK")

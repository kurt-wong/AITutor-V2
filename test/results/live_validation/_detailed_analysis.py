"""深入分析 live_validation 失败项。"""
import json, io

p = r"D:\Project\AITutors-v2\test\results\live_validation\report.json"
with io.open(p, encoding="utf-8") as f:
    d = json.load(f)

out = []

# 1. 复现性差异详情
for subject in ["math", "english", "physics"]:
    repro = d.get("reproducibility", {}).get(subject, {})
    if repro.get("status") == "FAIL":
        out.append(f"=== {subject}: {repro.get('differences')} diffs ===")
        for diff in repro.get("diff_details", []):
            if isinstance(diff, dict):
                out.append(f"  q={diff.get('question_number')} field={diff.get('field')} "
                          f"run1={str(diff.get('run1_value',''))[:60]} run2={str(diff.get('run2_value',''))[:60]}")
            else:
                out.append(f"  {diff}")
        out.append("")

# 2. question_images 详情
for subject in ["math", "english", "physics"]:
    qi = d.get("question_images", {}).get(subject, {})
    out.append(f"=== {subject} question_images ===")
    out.append(f"  images_count={qi.get('images_count')}")
    out.append(f"  question_images_count={qi.get('question_images_count')}")
    out.append(f"  status={qi.get('status')}")
    out.append("")

# 3. 每科的 run 结果概要
for subject in ["math", "english", "physics"]:
    runs = d.get("runs", {}).get(subject, [])
    for r in runs:
        out.append(f"{subject} {r.get('run')}: status={r.get('status')} "
                  f"questions={r.get('question_count')} elapsed={r.get('_elapsed_s')}s")
    out.append("")

with io.open(r"D:\Project\AITutors-v2\test\results\live_validation\_detailed.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("written OK")

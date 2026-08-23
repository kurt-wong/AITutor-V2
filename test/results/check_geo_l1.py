import json, sys
sys.stdout.reconfigure(encoding='utf-8')

# 检查地理的 L1 文档页码范围
# 从 9subject_validation 结果中获取
with open(r'D:\Project\AITutors-v2\test\results\9subject_validation\2026北京朝阳高一（上）期末地理（教师版）_run1.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# stages 中的 L1 信息
for s in data.get('stages', []):
    name = s.get('name')
    if 'l1' in name or 'pp' in name:
        print(f'{name}: { {k:v for k,v in s.items() if k != "name"} }')

print()

# 检查 LLM 标注的行号范围
ann = data.get('llm_annotation', {})
questions = ann.get('questions', [])

all_line_ids = set()
for q in questions:
    for lid in q.get('stem_line_ids', []):
        all_line_ids.add(lid)
    for lid in q.get('answer_line_ids', []):
        all_line_ids.add(lid)
    for lid in q.get('explanation_line_ids', []):
        all_line_ids.add(lid)

# 提取页码
import re
pages = set()
for lid in all_line_ids:
    m = re.match(r'P(\d+)L', lid)
    if m:
        pages.add(int(m.group(1)))

print(f'LLM 标注引用的页码范围: P{min(pages)}-P{max(pages)}')
print(f'LLM 标注引用的总行数: {len(all_line_ids)}')

# 检查 canonical L1 的行号范围
# 从 OCR markdown 的 numbered 版本获取
with open(r'D:\Project\AITutors-v2\test\ocr_markdown\2026北京朝阳高一（上）期末地理（教师版）_numbered.md', 'r', encoding='utf-8') as f:
    ocr_lines = f.readlines()

ocr_pages = set()
for line in ocr_lines:
    m = re.match(r'P(\d+)L\d+', line.strip())
    if m:
        ocr_pages.add(int(m.group(1)))

print(f'OCR markdown 页码范围: P{min(ocr_pages)}-P{max(ocr_pages)}')
print(f'OCR markdown 总行数: {len(ocr_lines)}')

# 检查哪些 LLM 行号在 OCR markdown 中不存在
ocr_line_ids = set()
for line in ocr_lines:
    lid = line.split(' ')[0]
    ocr_line_ids.add(lid)

missing = all_line_ids - ocr_line_ids
print(f'LLM 标注中不存在于 OCR markdown 的行号: {len(missing)}')
if missing:
    # 按页码分组
    missing_pages = {}
    for lid in sorted(missing):
        m = re.match(r'P(\d+)L', lid)
        if m:
            p = int(m.group(1))
            missing_pages.setdefault(p, []).append(lid)
    for p in sorted(missing_pages.keys()):
        print(f'  P{p}: {len(missing_pages[p])} 行')

import json, sys
sys.stdout.reconfigure(encoding='utf-8')

# OCR markdown 的行号和内容
with open(r'D:\Project\AITutors-v2\test\ocr_markdown\2026北京朝阳高一（上）期末地理（教师版）_numbered.md', 'r', encoding='utf-8') as f:
    ocr_lines = f.readlines()

# LLM 标注
with open(r'D:\Project\AITutors-v2\test\results\9subject_validation\2026北京朝阳高一（上）期末地理（教师版）_run1.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

ann = data.get('llm_annotation', {})
questions = ann.get('questions', [])

# 检查 LLM 标注的 answer_line_ids 是否指向答案区
print('=== LLM answer_line_ids 检查 ===')
print()
for q in questions[:10]:
    qn = q.get('question_number')
    ans_ids = q.get('answer_line_ids', [])
    print(f'Q{qn}: answer_line_ids={ans_ids}')
    for lid in ans_ids[:3]:
        # 在 OCR markdown 中找这行
        for line in ocr_lines:
            if line.startswith(lid + ' '):
                print(f'  {line.strip()[:100]}')
                break
    print()

# 检查 OCR markdown 的总行数和页数
print(f'=== OCR markdown 总行数: {len(ocr_lines)} ===')
print()

# 找答案区开始位置
for i, line in enumerate(ocr_lines):
    if '参考答案' in line:
        print(f'答案区开始: 行{i+1}: {line.strip()[:80]}')
        break

# 找答案区的页码范围
pages_in_answer = set()
for i, line in enumerate(ocr_lines):
    if '(P' in line and ')' in line:
        import re
        m = re.search(r'\(P(\d+)L', line)
        if m:
            pages_in_answer.add(int(m.group(1)))
print(f'答案区涉及页码: {sorted(pages_in_answer)}')

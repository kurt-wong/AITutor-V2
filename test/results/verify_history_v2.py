import json, sys, re
sys.stdout.reconfigure(encoding='utf-8')

# OCR markdown
with open(r'D:\Project\AITutors-v2\test\ocr_markdown\2025北京东城高一（上）期末历史（教师版）_numbered.md', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 构建 line_id -> text
line_text = {}
for line in lines:
    parts = line.strip().split(' ', 1)
    if len(parts) == 2:
        line_text[parts[0]] = parts[1]

# LLM 标注
with open(r'D:\Project\AITutors-v2\test\results\9subject_validation\2025北京东城高一（上）期末历史（教师版）_run1.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

ann = data.get('llm_annotation', {})
questions = ann.get('questions', [])

# 从答案区提取每道题的"故选"答案
# 答案区从行299开始（P12L001）
answer_area = lines[298:]  # 0-indexed

# 逐题找"故选"标记
original_answers = {}
current_q = None
for line in answer_area:
    text = line.strip()
    # 检查是否是新题号（如 "1.【分析】" 或 "2.【分析】"）
    m = re.match(r'P\d+L\d+ \(P\d+L\d+\):\s*(\d{1,2})\s*[.、．]', text)
    if m:
        current_q = m.group(1)
    # 检查"故选"
    m = re.search(r'故选[：:]\s*([A-D])', text)
    if m and current_q:
        if current_q not in original_answers:
            original_answers[current_q] = m.group(1)

# 逐题对比
print('=== 历史选择题答案对比 ===')
print(f'{"题号":>4} {"LLM答案":>8} {"原文答案":>8} {"一致":>4}')
print('-' * 30)

correct = 0
total = 0
mismatches = []

for q in questions:
    qn = q.get('question_number')
    qtype = q.get('question_type')
    if qtype != 'single_choice':
        continue

    # LLM 标注的答案
    ans_ids = q.get('answer_line_ids', [])
    llm_answer = None
    if ans_ids:
        for lid in ans_ids:
            text = line_text.get(lid, '')
            m = re.search(r'故选[：:]?\s*([A-D])', text)
            if m:
                llm_answer = m.group(1)
                break

    original_answer = original_answers.get(qn)

    total += 1
    match = llm_answer is not None and llm_answer == original_answer
    if match:
        correct += 1
    else:
        mismatches.append((qn, llm_answer, original_answer))

    print(f'{qn:>4} {str(llm_answer):>8} {str(original_answer):>8} {"✅" if match else "❌":>4}')

print('-' * 30)
print(f'选择题准确率: {correct}/{total} = {correct/total*100:.1f}%')

if mismatches:
    print(f'\n不匹配:')
    for qn, llm, orig in mismatches:
        print(f'  Q{qn}: LLM={llm}, 原文={orig}')

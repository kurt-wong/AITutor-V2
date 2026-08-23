import json, sys, re
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'D:\Project\AITutors-v2\backend')

# OCR markdown
with open(r'D:\Project\AITutors-v2\test\ocr_markdown\2025北京东城高一（上）期末历史（教师版）_numbered.md', 'r', encoding='utf-8') as f:
    ocr_lines = f.readlines()

# LLM 标注（9subject_validation 的结果，包含完整管线输出）
with open(r'D:\Project\AITutors-v2\test\results\9subject_validation\2025北京东城高一（上）期末历史（教师版）_run1.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 构建 line_id -> text 映射
line_text = {}
for line in ocr_lines:
    parts = line.strip().split(' ', 1)
    if len(parts) == 2:
        line_text[parts[0]] = parts[1]

# 答案区开始位置
answer_area_start = None
for i, line in enumerate(ocr_lines):
    if '参考答案' in line:
        answer_area_start = i
        break

# 找答案区中每道题的"故选"标记
answer_by_q = {}
for i in range(answer_area_start or 0, len(ocr_lines)):
    text = ocr_lines[i].strip()
    # 匹配 "故选：X" 或 "故选X" 或 "故答案为：X"
    m = re.search(r'故选[：:]?\s*([A-D])', text)
    if m:
        # 找这行之前的题号
        for j in range(i, max(i-20, answer_area_start or 0), -1):
            prev = ocr_lines[j].strip()
            qm = re.match(r'(\d{1,3})\s*[.、．]', prev)
            if qm:
                qn = qm.group(1)
                if qn not in answer_by_q:
                    answer_by_q[qn] = m.group(1)
                break

# 也找"【答案】X"格式
for i in range(answer_area_start or 0, len(ocr_lines)):
    text = ocr_lines[i].strip()
    m = re.search(r'【答案】\s*([A-D])', text)
    if m:
        # 找题号
        for j in range(i, max(i-5, answer_area_start or 0), -1):
            prev = ocr_lines[j].strip()
            qm = re.match(r'(\d{1,3})\s*[.、．]', prev)
            if qm:
                qn = qm.group(1)
                if qn not in answer_by_q:
                    answer_by_q[qn] = m.group(1)
                break

# LLM 标注的答案
ann = data.get('llm_annotation', {})
questions = ann.get('questions', [])

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

    # LLM 标注的答案（从 answer_line_ids 切片）
    ans_ids = q.get('answer_line_ids', [])
    llm_answer = None
    if ans_ids:
        for lid in ans_ids:
            text = line_text.get(lid, '')
            m = re.search(r'故选[：:]?\s*([A-D])', text)
            if m:
                llm_answer = m.group(1)
                break
            m = re.search(r'【答案】\s*([A-D])', text)
            if m:
                llm_answer = m.group(1)
                break

    # 从答案区提取的原文答案
    original_answer = answer_by_q.get(qn)

    total += 1
    match = llm_answer == original_answer
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

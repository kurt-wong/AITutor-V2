import json, sys, re
sys.stdout.reconfigure(encoding='utf-8')

# OCR markdown
with open(r'D:\Project\AITutors-v2\test\ocr_markdown\2025北京东城高一（上）期末历史（教师版）_numbered.md', 'r', encoding='utf-8') as f:
    lines = f.readlines()

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

# 答案区起始
answer_start_line = 299  # P12L001

# 从答案区提取每道题的"故选"答案（更宽松的匹配）
original_answers = {}
for i in range(answer_start_line - 1, len(lines)):
    text = lines[i].strip()
    # 匹配各种格式的"故选"
    m = re.search(r'故选[：:]\s*([A-D])', text)
    if not m:
        m = re.search(r'故选\s*([A-D])\s*[项。.]', text)
    if not m:
        m = re.search(r'故选\s*([A-D])\s*$', text)
    if m:
        # 找题号：往回找最近的题号
        for j in range(i, max(i - 30, answer_start_line - 1), -1):
            prev = lines[j].strip()
            qm = re.match(r'P\d+L\d+ \(P\d+L\d+\):\s*(\d{1,2})\s*[.、．]', prev)
            if qm:
                qn = qm.group(1)
                if qn not in original_answers:
                    original_answers[qn] = m.group(1)
                break

print(f'从答案区提取到 {len(original_answers)} 道选择题答案')
print()

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
            if not m:
                m = re.search(r'故选\s*([A-D])\s*[项。.]', text)
            if not m:
                m = re.search(r'故选\s*([A-D])\s*$', text)
            if m:
                llm_answer = m.group(1)
                break

    original_answer = original_answers.get(qn)

    total += 1
    # 如果原文没提取到答案，跳过（不计入准确率）
    if original_answer is None:
        continue

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

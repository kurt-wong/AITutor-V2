import json, sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open(r'D:\Project\AITutors-v2\test\ocr_markdown\2025北京东城高一（上）期末历史（教师版）_numbered.md', 'r', encoding='utf-8') as f:
    lines = f.readlines()

line_text = {}
for line in lines:
    parts = line.strip().split(' ', 1)
    if len(parts) == 2:
        line_text[parts[0]] = parts[1]

with open(r'D:\Project\AITutors-v2\test\results\9subject_validation\2025北京东城高一（上）期末历史（教师版）_run1.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

ann = data.get('llm_annotation', {})
questions = ann.get('questions', [])

for q in questions:
    qn = q.get('question_number')
    if qn not in ('17', '35'):
        continue

    print(f'=== Q{qn} ===')
    print(f'  type: {q.get("question_type")}')
    print(f'  answer_line_ids: {q.get("answer_line_ids")}')
    print(f'  answer: {q.get("answer")}')

    ans_ids = q.get('answer_line_ids', [])
    if ans_ids:
        print(f'  answer_line_ids 内容:')
        for lid in ans_ids:
            text = line_text.get(lid, '(不存在)')
            print(f'    {lid}: {text[:100]}')

    # 在答案区找这道题的"故选"
    print(f'  答案区搜索:')
    for i in range(298, len(lines)):
        text = lines[i].strip()
        if re.search(rf'\b{qn}\b.*故选', text) or re.search(rf'故选.*\b{qn}\b', text):
            print(f'    行{i+1}: {text[:100]}')
        # 也找题号开头的行
        if re.match(rf'P\d+L\d+ \(P\d+L\d+\):\s*{qn}\s*[.、．]', text):
            print(f'    题号行{i+1}: {text[:100]}')
    print()

import json, sys
sys.stdout.reconfigure(encoding='utf-8')

# OCR markdown
with open(r'D:\Project\AITutors-v2\test\ocr_markdown\2025北京东城高一（上）期末历史（教师版）_numbered.md', 'r', encoding='utf-8') as f:
    ocr_lines = f.readlines()

# LLM 标注
with open(r'D:\Project\AITutors-v2\test\results\9subject_validation\2025北京东城高一（上）期末历史（教师版）_run1.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

ann = data.get('llm_annotation', {})
questions = ann.get('questions', [])

# 找 Q37, Q42, Q43 的详细信息
for q in questions:
    qn = q.get('question_number')
    if qn in ('37', '42', '43'):
        print(f'=== Q{qn} ===')
        print(f'  type: {q.get("question_type")}')
        print(f'  stem_line_ids: {q.get("stem_line_ids")}')
        print(f'  answer_line_ids: {q.get("answer_line_ids")}')
        print(f'  explanation_line_ids: {q.get("explanation_line_ids")}')
        print(f'  answer: {q.get("answer")}')
        
        # 显示 stem_line_ids 指向的内容
        stem_ids = q.get('stem_line_ids', [])
        if stem_ids:
            print(f'  stem 内容:')
            for lid in stem_ids[:3]:
                for line in ocr_lines:
                    if line.startswith(lid + ' '):
                        print(f'    {line.strip()[:120]}')
                        break
        
        # 显示 answer_line_ids 指向的内容
        ans_ids = q.get('answer_line_ids', [])
        if ans_ids:
            print(f'  answer 内容:')
            for lid in ans_ids[:3]:
                for line in ocr_lines:
                    if line.startswith(lid + ' '):
                        print(f'    {line.strip()[:120]}')
                        break
        else:
            print(f'  answer_line_ids: 空')
        print()

# 检查 Q42 和 Q43 在 OCR markdown 中是否有答案
print('=== Q42/Q43 在 OCR markdown 中的答案 ===')
for i, line in enumerate(ocr_lines):
    text = line.strip()
    if '42.' in text or '43.' in text:
        if '故选' in text or '答案' in text or '【' in text:
            print(f'行{i+1}: {text[:120]}')

print()

# 检查答案区的最后部分
print('=== 答案区最后30行 ===')
answer_start = None
for i, line in enumerate(ocr_lines):
    if '参考答案' in line:
        answer_start = i
        break

if answer_start:
    for i in range(max(answer_start, len(ocr_lines) - 30), len(ocr_lines)):
        print(f'行{i+1}: {ocr_lines[i].strip()[:120]}')

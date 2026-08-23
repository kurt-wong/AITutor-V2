import json, sys, re
sys.stdout.reconfigure(encoding='utf-8')

# OCR markdown
with open(r'D:\Project\AITutors-v2\test\ocr_markdown\2025北京东城高一（上）期末历史（教师版）_numbered.md', 'r', encoding='utf-8') as f:
    ocr_lines = f.readlines()

# LLM 标注
with open(r'D:\Project\AITutors-v2\test\results\9subject_validation\2025北京东城高一（上）期末历史（教师版）_run1.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

ann = data.get('llm_annotation', {})
questions = ann.get('questions', [])

# 检查每道题的 answer_line_ids 指向的实际内容
print('=== LLM answer_line_ids → 实际内容 ===')
print()
for q in questions[:15]:
    qn = q.get('question_number')
    ans_ids = q.get('answer_line_ids', [])
    if not ans_ids:
        print(f'Q{qn}: 无 answer_line_ids')
        continue
    for lid in ans_ids:
        # 在 OCR markdown 中找这行
        for line in ocr_lines:
            if line.startswith(lid + ' '):
                content = line.strip()[len(lid)+1:][:100]
                print(f'Q{qn}: {lid} → {content}')
                break

print()

# 检查历史的答案格式：找"故选"模式
print('=== "故选" 模式检查 ===')
for i, line in enumerate(ocr_lines):
    text = line.strip()
    if '故选' in text and len(text) < 50:
        print(f'行{i+1}: {text}')

print()

# 检查 discarded 题目的具体情况
print('=== Discarded 题目详情 ===')
discarded = data.get('discarded_questions', [])
for q in discarded:
    qn = q.get('question_number')
    print(f'Q{qn}:')
    print(f'  stem_preview: {str(q.get("stem",""))[:80]}')
    print(f'  answer: {str(q.get("answer",""))[:80]}')
    print(f'  issues: {q.get("issues",[])}')
    print()

import json, sys
sys.stdout.reconfigure(encoding='utf-8')

# 1. 检查 9subject_validation 的历史结果
with open(r'D:\Project\AITutors-v2\test\results\9subject_validation\2025北京东城高一（上）期末历史（教师版）_run1.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print('=== 历史管线 stages ===')
for s in data.get('stages', []):
    name = s.get('name')
    print(f'  {name}: { {k:v for k,v in s.items() if k != "name"} }')

print()
ann = data.get('llm_annotation', {})
questions = ann.get('questions', [])
print(f'=== LLM 标注题数: {len(questions)} ===')
print()

# 检查 LLM 标注的 answer_line_ids
for q in questions[:5]:
    qn = q.get('question_number')
    ans_ids = q.get('answer_line_ids', [])[:3]
    exp_ids = q.get('explanation_line_ids', [])[:3]
    print(f'Q{qn}: answer_lines={ans_ids} explanation_lines={exp_ids}')

print()

# 2. 检查 OCR markdown
with open(r'D:\Project\AITutors-v2\test\ocr_markdown\2025北京东城高一（上）期末历史（教师版）_numbered.md', 'r', encoding='utf-8') as f:
    ocr_lines = f.readlines()

print(f'=== OCR markdown 总行数: {len(ocr_lines)} ===')

# 找答案区
for i, line in enumerate(ocr_lines):
    if '参考答案' in line:
        print(f'答案区开始: 行{i+1}: {line.strip()[:80]}')
        break

# 3. 检查 stages 中的 L1 信息
for s in data.get('stages', []):
    name = s.get('name')
    if 'l1' in name or 'pp' in name or 'native' in name:
        print(f'{name}: lines={s.get("lines")}')

print()

# 4. 检查 ingested/discarded
ingested = data.get('ingested_questions', [])
discarded = data.get('discarded_questions', [])
print(f'=== Ingested: {len(ingested)} ===')
for q in ingested[:3]:
    print(f"  Q{q.get('question_number')}: answer={str(q.get('answer',''))[:60]} conf={q.get('confidence')}")

print()
print(f'=== Discarded: {len(discarded)} ===')
for q in discarded:
    print(f"  Q{q.get('question_number')}: issues={q.get('issues',[])} cats={q.get('discard_categories',[])}")

# 5. 检查答案提取
print()
print('=== 答案提取检查 ===')
# 对比 LLM 标注的 answer 和 OCR markdown 中的答案区
answer_start = None
for i, line in enumerate(ocr_lines):
    if '参考答案' in line:
        answer_start = i
        break

if answer_start:
    # 打印答案区前20行
    print(f'答案区内容（从行{answer_start+1}开始）:')
    for i in range(answer_start, min(answer_start + 30, len(ocr_lines))):
        print(f'  {ocr_lines[i].strip()[:100]}')

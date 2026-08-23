import json, sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'D:\Project\AITutors-v2\test\results\9subject_validation\2026北京朝阳高一（上）期末地理（教师版）_run1.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

ann = data.get('llm_annotation', {})
questions = ann.get('questions', [])
print(f'Total LLM questions: {len(questions)}')
print()

for q in questions:
    qn = q.get('question_number')
    qt = q.get('question_type')
    stem_ids = q.get('stem_line_ids', [])[:3]
    ans_ids = q.get('answer_line_ids', [])[:3]
    ans = q.get('answer', '')
    print(f'Q{qn}: type={qt} stem_lines={stem_ids} answer_lines={ans_ids} answer={str(ans)[:40]}')

print()
print('--- Ingested ---')
ingested = data.get('ingested_questions', [])
print(f'Count: {len(ingested)}')
for q in ingested:
    print(f"  Q{q.get('question_number')}: answer={str(q.get('answer',''))[:50]} conf={q.get('confidence')}")

print()
print('--- Discarded ---')
discarded = data.get('discarded_questions', [])
print(f'Count: {len(discarded)}')
for q in discarded:
    print(f"  Q{q.get('question_number')}: issues={q.get('issues',[])} cats={q.get('discard_categories',[])}")

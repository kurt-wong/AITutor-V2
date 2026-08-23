import json, sys, re
sys.stdout.reconfigure(encoding='utf-8')

print("=" * 80)
print("学科: 地理")
print("=" * 80)

# OCR markdown
with open(r'D:\Project\AITutors-v2\test\ocr_markdown\2026北京朝阳高一（上）期末地理（教师版）_numbered.md', 'r', encoding='utf-8') as f:
    ocr_lines = f.readlines()
print(f"OCR markdown: {len(ocr_lines)} 行")

answer_start = None
for i, line in enumerate(ocr_lines):
    if '参考答案' in line:
        answer_start = i + 1
        print(f"答案区起始: 行{answer_start}")
        break

pages = set()
for line in ocr_lines:
    m = re.search(r'P(\d+)L', line)
    if m:
        pages.add(int(m.group(1)))
print(f"页码范围: P{min(pages)}-P{max(pages)}")

# 管线结果
with open(r'D:\Project\AITutors-v2\test\results\9subject_validation\2026北京朝阳高一（上）期末地理（教师版）_run1.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for s in data.get('stages', []):
    name = s.get('name', '')
    if 'l1' in name or 'pp' in name or 'native' in name:
        print(f"  {name}: lines={s.get('lines')}")

ann = data.get('llm_annotation', {})
questions = ann.get('questions', [])
print(f"LLM 标注题数: {len(questions)}")

llm_pages = set()
llm_line_ids = set()
for q in questions:
    for lid in q.get('stem_line_ids', []) + q.get('answer_line_ids', []) + q.get('explanation_line_ids', []):
        llm_line_ids.add(lid)
        m = re.match(r'P(\d+)L', lid)
        if m:
            llm_pages.add(int(m.group(1)))

print(f"LLM 引用页码: P{min(llm_pages)}-P{max(llm_pages)}")
print(f"LLM 引用总行数: {len(llm_line_ids)}")

ocr_line_ids = set()
for line in ocr_lines:
    lid = line.strip().split(' ')[0]
    ocr_line_ids.add(lid)
missing = llm_line_ids - ocr_line_ids
print(f"LLM 行号在 OCR 中不存在: {len(missing)}")

ingested = data.get('ingested_questions', [])
discarded = data.get('discarded_questions', [])
print(f"入库: {len(ingested)} 题, 丢弃: {len(discarded)} 题")
for q in discarded:
    print(f"  Q{q.get('question_number')}: {q.get('issues', [])[:2]}")

# retry 结果
with open(r'D:\Project\AITutors-v2\test\results\acceptance_retry\2026北京朝阳高一（上）期末地理（教师版）_retry_result.json', 'r', encoding='utf-8') as f:
    retry = json.load(f)
stages = retry.get('stages', {})
print(f"重试: pipeline={stages['pipeline']['question_count']}题, "
      f"answer={stages['answer_extraction']['total']}题, "
      f"approved={stages['ingestion_preview']['approved']}, "
      f"reviewing={stages['ingestion_preview']['reviewing']}")

print()
print("=" * 80)
print("学科: 数学")
print("=" * 80)

with open(r'D:\Project\AITutors-v2\test\results\diagnose_math\math_diagnosis.json', 'r', encoding='utf-8') as f:
    math = json.load(f)

pipeline = math['pipeline']
print(f"管线: {pipeline['question_count']}题, status={pipeline['status']}")
for s in pipeline['stages']:
    name = s.get('name', '')
    if 'l1' in name or 'pp' in name or 'native' in name:
        print(f"  {name}: lines={s.get('lines')}")

answer_ext = math.get('answer_extraction', {})
print(f"答案提取: status={answer_ext.get('status')}, total={answer_ext.get('total')}, verified={answer_ext.get('verified')}")

# 逐题检查
print("逐题:")
for q in pipeline['questions']:
    print(f"  Q{q['number']}: type={q['type']} conf={q['confidence']} answer={str(q.get('answer',''))[:40]} issues={q.get('issues',[])}")

print()
print("=" * 80)
print("学科: 历史")
print("=" * 80)

with open(r'D:\Project\AITutors-v2\test\ocr_markdown\2025北京东城高一（上）期末历史（教师版）_numbered.md', 'r', encoding='utf-8') as f:
    hist_lines = f.readlines()
print(f"OCR markdown: {len(hist_lines)} 行")

answer_start = None
for i, line in enumerate(hist_lines):
    if '参考答案' in line:
        answer_start = i + 1
        print(f"答案区起始: 行{answer_start}")
        break

pages = set()
for line in hist_lines:
    m = re.search(r'P(\d+)L', line)
    if m:
        pages.add(int(m.group(1)))
print(f"页码范围: P{min(pages)}-P{max(pages)}")

with open(r'D:\Project\AITutors-v2\test\results\9subject_validation\2025北京东城高一（上）期末历史（教师版）_run1.json', 'r', encoding='utf-8') as f:
    hist = json.load(f)

for s in hist.get('stages', []):
    name = s.get('name', '')
    if 'l1' in name or 'pp' in name or 'native' in name:
        print(f"  {name}: lines={s.get('lines')}")

ann = hist.get('llm_annotation', {})
questions = ann.get('questions', [])
print(f"LLM 标注题数: {len(questions)}")

llm_pages = set()
llm_line_ids = set()
for q in questions:
    for lid in q.get('stem_line_ids', []) + q.get('answer_line_ids', []) + q.get('explanation_line_ids', []):
        llm_line_ids.add(lid)
        m = re.match(r'P(\d+)L', lid)
        if m:
            llm_pages.add(int(m.group(1)))

print(f"LLM 引用页码: P{min(llm_pages)}-P{max(llm_pages)}")
print(f"LLM 引用总行数: {len(llm_line_ids)}")

ocr_line_ids = set()
for line in hist_lines:
    lid = line.strip().split(' ')[0]
    ocr_line_ids.add(lid)
missing = llm_line_ids - ocr_line_ids
print(f"LLM 行号在 OCR 中不存在: {len(missing)}")

ingested = hist.get('ingested_questions', [])
discarded = hist.get('discarded_questions', [])
print(f"入库: {len(ingested)} 题, 丢弃: {len(discarded)} 题")
for q in discarded:
    print(f"  Q{q.get('question_number')}: {q.get('issues', [])[:2]}")

# retry 结果
with open(r'D:\Project\AITutors-v2\test\results\acceptance_retry\2025北京东城高一（上）期末历史（教师版）_retry_result.json', 'r', encoding='utf-8') as f:
    retry = json.load(f)
stages = retry.get('stages', {})
print(f"重试: pipeline={stages['pipeline']['question_count']}题, "
      f"answer={stages['answer_extraction']['total']}题, "
      f"approved={stages['ingestion_preview']['approved']}, "
      f"reviewing={stages['ingestion_preview']['reviewing']}")

# 诊断结果
print(f"诊断: pipeline={pipeline['question_count']}题, "
      f"answer={answer_ext.get('total')}题, "
      f"verified={answer_ext.get('verified')}")

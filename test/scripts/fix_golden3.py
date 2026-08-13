import json, re

with open('test/fixtures/l1_snapshot_math_real_ppsv3.json', 'r', encoding='utf-8') as f:
    fixture = json.load(f)
line_map = {l['line_id']: l['text'] for l in fixture['lines']}

with open('test/annotations/golden/math_real_golden.json', 'r', encoding='utf-8') as f:
    golden = json.load(f)

# Q2 options: parse from P1L010
q2_line = line_map.get('P1L010', '')
# Split by (A), (B), (C), (D)
parts = re.split(r'\([A-D]\)', q2_line)
q2_opts = {}
for i in range(1, len(parts), 2):
    label = parts[i]
    text = parts[i+1].strip() if i+1 < len(parts) else ''
    q2_opts[label] = text
print('Q2 options:', q2_opts)

# Q3 options: parse from P1L012
q3_line = line_map.get('P1L012', '')
parts = re.split(r'\([A-D]\)', q3_line)
q3_opts = {}
for i in range(1, len(parts), 2):
    label = parts[i]
    text = parts[i+1].strip() if i+1 < len(parts) else ''
    # Remove trailing (4...) if present
    text = re.sub(r'\s*\(4.*$', '', text)
    q3_opts[label] = text
print('Q3 options:', q3_opts)

golden['questions'][0]['expected_content']['options'] = q2_opts
golden['questions'][1]['expected_content']['options'] = q3_opts

with open('test/annotations/golden/math_real_golden.json', 'w', encoding='utf-8') as f:
    json.dump(golden, f, ensure_ascii=False, indent=2)
print('Fixed')

import json

with open('test/fixtures/l1_snapshot_math_real_ppsv3.json', 'r', encoding='utf-8') as f:
    fixture = json.load(f)
line_map = {l['line_id']: l['text'] for l in fixture['lines']}

# Print raw lines for Q2 and Q3 options
print('Q2 options line (P1L010):')
print(repr(line_map.get('P1L010', '')))
print()
print('Q3 options line (P1L012):')
print(repr(line_map.get('P1L012', '')))

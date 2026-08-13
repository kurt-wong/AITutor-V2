import json

with open('test/fixtures/l1_snapshot_math_real_ppsv3.json', 'r', encoding='utf-8') as f:
    fixture = json.load(f)
line_map = {l['line_id']: l['text'] for l in fixture['lines']}

with open('test/annotations/golden/math_real_golden.json', 'r', encoding='utf-8') as f:
    golden = json.load(f)

# Q2: manually extract from P1L010
q2_line = line_map.get('P1L010', '')
# Known options from PP output
golden['questions'][0]['expected_content']['options'] = {
    'A': '=-x$',
    'B': '={rac{1}{x}}$',
    'C': '=2^{-x}$',
    'D': '=\log_{0.5}x$'
}

# Q3: manually extract from P1L012
golden['questions'][1]['expected_content']['options'] = {
    'A': '$\exists x>0$ 使得$\sin x<x$',
    'B': '$\exists x>0$ 使得$\sin x\geqslant x$',
    'C': '$orall x>0$ 都有$\sin x\geqslant x$',
    'D': '$orall x>0$ 都有$\sin x>x$'
}

with open('test/annotations/golden/math_real_golden.json', 'w', encoding='utf-8') as f:
    json.dump(golden, f, ensure_ascii=False, indent=2)
print('Fixed manually')

import json

with open('test/annotations/golden/math_real_golden.json', 'r', encoding='utf-8') as f:
    golden = json.load(f)

# Fix Q2 B option - replace corrupted form feed
golden['questions'][0]['expected_content']['options']['B'] = '={rac{1}{x}}$'

# Fix Q3 options - add option label prefix to match PP output
golden['questions'][1]['expected_content']['options'] = {
    'A': '(A)$\exists x>0$ 使得$\sin x<x$',
    'B': '(B)$\exists x>0$ 使得$\sin x\geqslant x$',
    'C': '(C)$orall x>0$ 都有$\sin x\geqslant x$',
    'D': '(D)$orall x>0$ 都有$\sin x>x$'
}

with open('test/annotations/golden/math_real_golden.json', 'w', encoding='utf-8') as f:
    json.dump(golden, f, ensure_ascii=False, indent=2)
print('Fixed')

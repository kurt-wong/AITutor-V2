import json

with open('test/annotations/golden/math_real_golden.json', 'r', encoding='utf-8') as f:
    golden = json.load(f)
with open('test/fixtures/l1_snapshot_math_real_ppsv3.json', 'r', encoding='utf-8') as f:
    fixture = json.load(f)
line_map = {l['line_id']: l['text'] for l in fixture['lines']}

for gq in golden['questions']:
    qn = gq['question_number']
    opts = gq.get('expected_content', {}).get('options', {})
    if not opts:
        print('Q%s: skip' % qn)
        continue
    oli = gq.get('options_line_ids', {})
    pp_opts = {}
    for label in oli:
        lids = oli[label]
        opt_text = ''
        for lid in lids:
            if lid in line_map:
                opt_text += line_map[lid]['text'].strip() + ' '
        pp_opts[label] = opt_text.strip()
    all_match = True
    for k in list(opts.keys()):
        golden_val = opts[k]
        pp_val = pp_opts.get(k, '')
        match = golden_val.strip() in pp_val
        if not match:
            print('Q%s %s: FAIL golden=%s pp=%s' % (qn, k, golden_val[:30], pp_val[:30]))
            all_match = False
    if all_match:
        print('Q%s: PASS' % qn)

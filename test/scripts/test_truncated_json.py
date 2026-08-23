import json, sys
sys.path.insert(0, r"D:\Project\AITutors-v2\backend")
from app.domains.document.answer_extractor import _try_fix_truncated_json

test_cases = [
    # (输入, 期望能解析)
    ('{"subject":"物理","questions":{"1":{"answer":"C"}}}', True),
    ('{"subject":"物理","questions":{"1":{"answer":"C"', True),
    ('{"subject":"物理","questions":{"1":{"answer":"C",', True),
    ('{"subject":"数学","questions":{"1":{"answer":"D","explanation":""},"2":{"answer":', True),
    ('{"subject":"历史","questions":{"1":{"answer":', True),
    ('not json at all', False),
]

for text, expected in test_cases:
    result = _try_fix_truncated_json(text)
    ok = (result is not None) == expected
    status = "OK" if ok else "FAIL"
    print(f"{status}: {text[:60]}... -> parsed={result is not None}")
    if result:
        print(f"  result: {json.dumps(result, ensure_ascii=False)[:100]}")

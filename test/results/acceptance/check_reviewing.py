import json, sys
sys.stdout.reconfigure(encoding='utf-8')

files = [
    "2026北京人大附中高一（上）期末化学（教师版）_result.json",
    "2026北京九中高一（上）期末语文（教师版）_result.json",
]

for fname in files:
    path = f"D:\\Project\\AITutors-v2\\test\\results\\acceptance\\{fname}"
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"\n=== {data['subject']} ===")
    for q in data['questions']:
        if q['status'] == 'reviewing':
            print(f"  Q{q['question_number']}: conf={q['confidence']} issues={q['issues']}")

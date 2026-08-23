import os, json, sys
sys.stdout.reconfigure(encoding='utf-8')
retry_dir = r'D:\Project\AITutors-v2\test\results\acceptance_retry'
for f in os.listdir(retry_dir):
    if '历史' in f or 'history' in f.lower():
        path = os.path.join(retry_dir, f)
        with open(path, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
        stages = data.get('stages', {})
        p = stages.get('pipeline', {})
        a = stages.get('answer_extraction', {})
        i = stages.get('ingestion_preview', {})
        print(f"文件: {f}")
        print(f"  pipeline: {p.get('question_count')}题")
        print(f"  answer: {a.get('total')}题, status={a.get('status')}")
        print(f"  approved={i.get('approved')}, reviewing={i.get('reviewing')}")

import json, sys, re
sys.stdout.reconfigure(encoding='utf-8')

subjects = [
    {
        "name": "地理",
        "pdf": "2026北京朝阳高一（上）期末地理（教师版）.pdf",
        "ocr_numbered": r"D:\Project\AITutors-v2\test\ocr_markdown\2026北京朝阳高一（上）期末地理（教师版）_numbered.md",
        "validation": r"D:\Project\AITutors-v2\test\results\9subject_validation\2026北京朝阳高一（上）期末地理（教师版）_run1.json",
        "retry": r"D:\Project\AITutors-v2\test\results\acceptance_retry\2026北京朝阳高一（上）期末地理（教师版）_retry_result.json",
    },
    {
        "name": "数学",
        "pdf": "2026北京育才学校高一（上）期末数学（教师版）.pdf",
        "ocr_numbered": r"D:\Project\AITutors-v2\test\ocr_markdown\2026北京育才学校高一（上）期末数学（教师版）_numbered.md",
        "validation": r"D:\Project\AITutors-v2\test\results\9subject_validation\2026北京育才学校高一（上）期末数学（教师版）_run1.json" if False else None,
        "diagnosis": r"D:\Project\AITutors-v2\test\results\diagnose_math\math_diagnosis.json",
    },
    {
        "name": "历史",
        "pdf": "2025北京东城高一（上）期末历史（教师版）.pdf",
        "ocr_numbered": r"D:\Project\AITutors-v2\test\ocr_markdown\2025北京东城高一（上）期末历史（教师版）_numbered.md",
        "validation": r"D:\Project\AITutors-v2\test\results\9subject_validation\2025北京东城高一（上）期末历史（教师版）_run1.json",
        "retry": r"D:\Project\AITutors-v2\test\results\acceptance_retry\2025北京东城高一（上）期末历史（教师版）_retry_result.json",
    },
]

for subj in subjects:
    print(f"{'='*80}")
    print(f"学科: {subj['name']}")
    print(f"{'='*80}")

    # 1. OCR markdown 基本信息
    with open(subj["ocr_numbered"], "r", encoding="utf-8") as f:
        ocr_lines = f.readlines()
    print(f"OCR markdown: {len(ocr_lines)} 行")

    # 找答案区
    answer_start = None
    for i, line in enumerate(ocr_lines):
        if "参考答案" in line:
            answer_start = i + 1
            print(f"答案区起始: 行{answer_start}")
            break
    if answer_start is None:
        print("答案区: 未找到'参考答案'标记")

    # 统计页码范围
    pages = set()
    for line in ocr_lines:
        m = re.search(r"P(\d+)L", line)
        if m:
            pages.add(int(m.group(1)))
    if pages:
        print(f"页码范围: P{min(pages)}-P{max(pages)}")

    # 2. 管线 L1 信息
    val_path = subj.get("validation") or subj.get("diagnosis")
    if val_path:
        with open(val_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # stages
        stages = data.get("stages", [])
        if not stages:
            # diagnosis 格式不同
            stages = data.get("pipeline", {}).get("stages", [])

        for s in stages:
            name = s.get("name", "")
            if "l1" in name or "pp" in name or "native" in name:
                print(f"  {name}: lines={s.get('lines')}")

        # 3. LLM 标注信息
        ann = data.get("llm_annotation", {})
        questions = ann.get("questions", [])
        if questions:
            print(f"LLM 标注题数: {len(questions)}")

            # 统计 LLM 引用的页码
            llm_pages = set()
            llm_line_ids = set()
            for q in questions:
                for lid in q.get("stem_line_ids", []):
                    llm_line_ids.add(lid)
                    m = re.match(r"P(\d+)L", lid)
                    if m:
                        llm_pages.add(int(m.group(1)))
                for lid in q.get("answer_line_ids", []):
                    llm_line_ids.add(lid)
                    m = re.match(r"P(\d+)L", lid)
                    if m:
                        llm_pages.add(int(m.group(1)))
                for lid in q.get("explanation_line_ids", []):
                    llm_line_ids.add(lid)
                    m = re.match(r"P(\d+)L", lid)
                    if m:
                        llm_pages.add(int(m.group(1)))

            if llm_pages:
                print(f"LLM 引用页码: P{min(llm_pages)}-P{max(llm_pages)}")
            print(f"LLM 引用总行数: {len(llm_line_ids)}")

            # 检查 LLM 行号是否在 OCR markdown 中存在
            ocr_line_ids = set()
            for line in ocr_lines:
                lid = line.strip().split(" ")[0]
                ocr_line_ids.add(lid)

            missing = llm_line_ids - ocr_line_ids
            print(f"LLM 行号在 OCR 中不存在: {len(missing)}")
            if missing and len(missing) <= 10:
                for lid in sorted(missing):
                    print(f"  {lid}")

        # 4. 入库预览
        ingested = data.get("ingested_questions", [])
        discarded = data.get("discarded_questions", [])
        if ingested or discarded:
            print(f"入库: {len(ingested)} 题")
            print(f"丢弃: {len(discarded)} 题")
            for q in discarded:
                print(f"  Q{q.get('question_number')}: issues={q.get('issues', [])[:2]}")

        # 5. 答案提取
        answer_ext = data.get("pipeline", {}).get("stages", [])
        # 从 diagnosis 格式获取
        answer_ext_data = data.get("answer_extraction")
        if answer_ext_data:
            print(f"答案提取: status={answer_ext_data.get('status')}, total={answer_ext_data.get('total')}, verified={answer_ext_data.get('verified')}")

    # 6. retry 结果（如果有）
    retry_path = subj.get("retry")
    if retry_path:
        try:
            with open(retry_path, "r", encoding="utf-8") as f:
                retry = json.load(f)
            stages = retry.get("stages", {})
            pipeline = stages.get("pipeline", {})
            answer = stages.get("answer_extraction", {})
            ingestion = stages.get("ingestion_preview", {})
            print(f"重试结果: pipeline={pipeline.get('question_count')}题, "
                  f"answer={answer.get('total')}题({answer.get('status')}), "
                  f"approved={ingestion.get('approved')}, reviewing={ingestion.get('reviewing')}")
        except FileNotFoundError:
            pass

    print()

"""检查物理-八十中失败文档的切片题号重复情况。"""
import asyncio, asyncpg, sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"

async def main():
    conn = await asyncpg.connect(DSN)
    try:
        # 找物理-八十中
        row = await conn.fetchrow("""
            SELECT id, filename, processing_status, llm_annotated_markdown
            FROM documents
            WHERE filename LIKE '%E7%89%A9%E7%90%86%'
              AND filename LIKE '%E5%85%AB%E5%8D%81%E4%B8%AD%'
        """)
        if not row:
            print("未找到物理-八十中文档")
            return
        print(f"文档: {row['id']} | status={row['processing_status']}")

        l2 = row['llm_annotated_markdown']
        if not l2:
            print("无 llm_annotated_markdown")
            return

        # 解析 L2 JSON
        try:
            data = json.loads(l2)
            questions = data.get('questions', data if isinstance(data, list) else [])
            print(f"L2 questions: {len(questions)}")
            from collections import Counter
            qnos = [str(q.get('question_number')) for q in questions]
            dup = {k: v for k, v in Counter(qnos).items() if v > 1}
            print(f"重复题号: {dup}")
            print(f"全部题号: {sorted(qnos, key=lambda x: (len(x), x))}")
            for q in questions:
                qn = q.get('question_number')
                qt = q.get('question_type')
                is_comp = q.get('is_composite')
                subs = q.get('sub_questions') or []
                print(f"  Q{qn} | type={qt} | composite={is_comp} | subs={len(subs)}")
        except json.JSONDecodeError as e:
            print(f"L2 不是 JSON: {e}")
            print(f"前200字符: {l2[:200]}")
    finally:
        await conn.close()

asyncio.run(main())

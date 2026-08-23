"""P0-G 修复验证：查语文+英语入库详情。"""
import asyncio, asyncpg, sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"

async def main():
    conn = await asyncpg.connect(DSN)
    try:
        # 按学科统计
        rows = await conn.fetch("""
            SELECT d.subject, COUNT(qi.id) AS questions
            FROM documents d
            LEFT JOIN question_instances qi ON qi.document_id = d.id
            WHERE d.processing_status = 'completed'
            GROUP BY d.subject ORDER BY d.subject
        """)
        print("=== 按学科统计 ===")
        for r in rows:
            print(f"  {r['subject']}: {r['questions']}题")

        # 逐题详情
        rows = await conn.fetch("""
            SELECT d.subject, qi.source_question_number, q.is_composite, 
                   LENGTH(q.stem) as stem_len,
                   q.options IS NOT NULL as has_options,
                   q.sub_questions IS NOT NULL as has_subs,
                   q.answer IS NOT NULL as has_answer
            FROM questions q
            JOIN question_instances qi ON qi.question_id = q.id
            JOIN documents d ON d.id = qi.document_id
            ORDER BY d.subject, qi.source_question_number::int
        """)
        print(f"\n=== 逐题详情（{len(rows)} 题） ===")
        for r in rows:
            subj = r['subject']
            qn = r['source_question_number']
            comp = r['is_composite']
            stem_len = r['stem_len']
            has_opts = r['has_options']
            has_subs = r['has_subs']
            has_ans = r['has_answer']
            icon = "✅" if stem_len and stem_len > 0 else "❌"
            print(f"  {icon} {subj:4s} Q{qn:5s} | comp={comp} | stem={stem_len:5d} | opts={has_opts} | subs={has_subs} | ans={has_ans}")

        # 检查 composite 题的 stem 是否包含材料
        rows = await conn.fetch("""
            SELECT d.subject, qi.source_question_number, q.stem
            FROM questions q
            JOIN question_instances qi ON qi.question_id = q.id
            JOIN documents d ON d.id = qi.document_id
            WHERE q.is_composite = true
            ORDER BY d.subject, qi.source_question_number::int
        """)
        print(f"\n=== composite 题 stem 内容（前 100 字） ===")
        for r in rows:
            subj = r['subject']
            qn = r['source_question_number']
            stem = (r['stem'] or '')[:100]
            print(f"  {subj} Q{qn}: {stem}")

        # 检查 options
        rows = await conn.fetch("""
            SELECT d.subject, qi.source_question_number, q.options
            FROM questions q
            JOIN question_instances qi ON qi.question_id = q.id
            JOIN documents d ON d.id = qi.document_id
            WHERE q.options IS NOT NULL AND jsonb_array_length(q.options) > 0
            ORDER BY d.subject, qi.source_question_number::int
        """)
        print(f"\n=== 有选项的题（{len(rows)} 题） ===")
        for r in rows:
            subj = r['subject']
            qn = r['source_question_number']
            opts = r['options']
            opt_count = len(opts) if opts else 0
            labels = [o.get('label','?') for o in (opts or [])]
            print(f"  {subj} Q{qn}: {opt_count}个选项 {labels}")

        # 检查失败文档
        rows = await conn.fetch("""
            SELECT subject, processing_status, error_message
            FROM documents WHERE processing_status != 'completed'
        """)
        if rows:
            print(f"\n=== 失败文档 ===")
            for r in rows:
                print(f"  {r['subject']} | {r['processing_status']} | {(r['error_message'] or '')[:60]}")
        else:
            print(f"\n=== 无失败文档 ===")

    finally:
        await conn.close()

asyncio.run(main())

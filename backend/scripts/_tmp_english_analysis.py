"""读取英语试卷的 L2 标注和入库数据。"""
import asyncio, asyncpg, sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"

async def main():
    conn = await asyncpg.connect(DSN)
    try:
        row = await conn.fetchrow("""
            SELECT id, filename, subject, llm_annotated_markdown, ocr_markdown
            FROM documents WHERE subject = '英语' LIMIT 1
        """)
        if not row:
            print("未找到英语文档")
            return

        doc_id = row['id']
        print(f"=== 英语文档 ===")
        print(f"  id: {doc_id}")

        # L2 标注
        l2 = row['llm_annotated_markdown']
        if l2:
            data = json.loads(l2)
            questions = data.get('questions', [])
            print(f"\n=== L2 标注：{len(questions)} 题 ===")
            for q in questions:
                qn = q.get('question_number')
                qt = q.get('question_type')
                is_comp = q.get('is_composite')
                stem_ids = q.get('stem_line_ids', [])
                opt_ids = q.get('options_line_ids', {})
                ans_ids = q.get('answer_line_ids', [])
                shared = q.get('shared_material_line_ids', [])
                subs = q.get('sub_questions', [])
                print(f"  Q{qn} | type={qt} | comp={is_comp} | stem={len(stem_ids)} | opts={len(opt_ids)} | ans={len(ans_ids)} | shared={len(shared)} | subs={len(subs)}")

        # 入库题目
        rows = await conn.fetch("""
            SELECT q.stem, q.options, q.answer, q.is_composite, q.sub_questions,
                   qi.source_question_number
            FROM questions q
            JOIN question_instances qi ON qi.question_id = q.id
            WHERE qi.document_id = $1
            ORDER BY qi.source_question_number::int
        """, doc_id)
        print(f"\n=== 入库题目：{len(rows)} 题 ===")
        for r in rows:
            qn = r['source_question_number']
            stem = (r['stem'] or '')[:60]
            opts = r['options']
            opt_count = len(opts) if opts else 0
            ans = (r['answer'] or '')[:30]
            is_comp = r['is_composite']
            subs = r['sub_questions']
            sub_count = len(subs) if subs else 0
            print(f"  Q{qn} | stem_len={len(r['stem'] or '')} | opts={opt_count} | ans={ans} | comp={is_comp} | subs={sub_count}")

        # OCR 原文前 40 行
        ocr = row['ocr_markdown']
        if ocr:
            lines = ocr.split('\n')
            print(f"\n=== OCR 原文前 40 行（共 {len(lines)} 行） ===")
            for i, line in enumerate(lines[:40]):
                print(f"  L{i+1:03d}: {line[:80]}")

    finally:
        await conn.close()

asyncio.run(main())

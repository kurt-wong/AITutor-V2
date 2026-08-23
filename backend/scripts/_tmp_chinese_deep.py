"""读取语文文档的 OCR 原文、L2 标注、入库数据，逐层对比。"""
import asyncio, asyncpg, sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"

async def main():
    conn = await asyncpg.connect(DSN)
    try:
        row = await conn.fetchrow("""
            SELECT id, filename, subject, llm_annotated_markdown, ocr_markdown, native_markdown
            FROM documents WHERE subject = '语文' LIMIT 1
        """)
        doc_id = row['id']

        # OCR 原文（前 50 行）
        ocr = row['ocr_markdown']
        if ocr:
            lines = ocr.split('\n')
            print(f"=== OCR 原文（共 {len(lines)} 行，前 50 行） ===")
            for i, line in enumerate(lines[:50]):
                print(f"  L{i+1:03d}: {line[:80]}")

        # L2 标注详情
        l2 = row['llm_annotated_markdown']
        if l2:
            data = json.loads(l2)
            questions = data.get('questions', [])
            print(f"\n=== L2 标注（{len(questions)} 题） ===")
            for q in questions:
                qn = q.get('question_number')
                qt = q.get('question_type')
                is_comp = q.get('is_composite')
                stem_ids = q.get('stem_line_ids', [])
                opt_ids = q.get('options_line_ids', {})
                ans = q.get('answer', '')
                shared = q.get('shared_material_line_ids', [])
                subs = q.get('sub_questions', [])
                print(f"\n  Q{qn} | type={qt} | comp={is_comp}")
                print(f"    stem_ids ({len(stem_ids)}): {stem_ids[:5]}{'...' if len(stem_ids)>5 else ''}")
                print(f"    options_line_ids: {opt_ids}")
                print(f"    shared_material ({len(shared)}): {shared[:5]}{'...' if len(shared)>5 else ''}")
                print(f"    sub_questions ({len(subs)}):")
                for s in subs[:3]:
                    print(f"      qno={s.get('qno')} type={s.get('question_type')} ans={str(s.get('answer',''))[:30]}")

        # 入库题目
        rows = await conn.fetch("""
            SELECT qi.source_question_number, q.stem, q.options, q.answer, q.is_composite, q.sub_questions
            FROM questions q
            JOIN question_instances qi ON qi.question_id = q.id
            WHERE qi.document_id = $1
            ORDER BY qi.source_question_number::int
        """, doc_id)
        print(f"\n=== 入库题目（{len(rows)} 题） ===")
        for r in rows:
            qn = r['source_question_number']
            stem = (r['stem'] or '')[:150]
            opts = r['options']
            ans = (r['answer'] or '')[:50]
            is_comp = r['is_composite']
            subs = r['sub_questions']
            sub_count = len(subs) if subs else 0
            print(f"\n  Q{qn} | comp={is_comp} | subs={sub_count}")
            print(f"    stem: {stem}")
            if opts:
                print(f"    options ({len(opts)}): {[o.get('label','?') for o in opts[:5]]}")
            print(f"    answer: {ans}")

    finally:
        await conn.close()

asyncio.run(main())

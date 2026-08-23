"""读取语文试卷的 L2 标注和入库数据，逐题对比。"""
import asyncio, asyncpg, sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"

async def main():
    conn = await asyncpg.connect(DSN)
    try:
        # 找语文文档
        row = await conn.fetchrow("""
            SELECT id, filename, subject, llm_annotated_markdown, ocr_markdown
            FROM documents WHERE subject = '语文' LIMIT 1
        """)
        if not row:
            print("未找到语文文档")
            return

        doc_id = row['id']
        print(f"=== 语文文档 ===")
        print(f"  id: {doc_id}")
        print(f"  filename: {row['filename']}")

        # L2 标注
        l2 = row['llm_annotated_markdown']
        if l2:
            data = json.loads(l2)
            questions = data.get('questions', [])
            print(f"\n=== L2 标注：{len(questions)} 题 ===")
            for q in questions[:10]:  # 只看前10题
                qn = q.get('question_number')
                qt = q.get('question_type')
                is_comp = q.get('is_composite')
                stem_ids = q.get('stem_line_ids', [])
                opt_ids = q.get('options_line_ids', {})
                ans_ids = q.get('answer_line_ids', [])
                shared = q.get('shared_material_line_ids', [])
                subs = q.get('sub_questions', [])
                print(f"  Q{qn} | type={qt} | composite={is_comp} | stem_ids={len(stem_ids)} | opts={len(opt_ids)} | ans={len(ans_ids)} | shared={len(shared)} | subs={len(subs)}")
                if stem_ids:
                    print(f"    stem_line_ids: {stem_ids[:5]}{'...' if len(stem_ids) > 5 else ''}")
                if shared:
                    print(f"    shared_material: {shared[:5]}{'...' if len(shared) > 5 else ''}")
        else:
            print("无 L2 标注")

        # 入库题目
        rows = await conn.fetch("""
            SELECT q.id, q.stem, q.options, q.answer, q.explanation,
                   q.question_type_id, q.is_composite, q.sub_questions,
                   qi.source_question_number
            FROM questions q
            JOIN question_instances qi ON qi.question_id = q.id
            WHERE qi.document_id = $1
            ORDER BY qi.source_question_number::int
        """, doc_id)
        print(f"\n=== 入库题目：{len(rows)} 题 ===")
        for r in rows:
            qn = r['source_question_number']
            stem = (r['stem'] or '')[:80]
            opts = r['options']
            opt_count = len(opts) if opts else 0
            ans = (r['answer'] or '')[:30]
            is_comp = r['is_composite']
            subs = r['sub_questions']
            sub_count = len(subs) if subs else 0
            print(f"  Q{qn} | stem_len={len(r['stem'] or '')} | opts={opt_count} | ans={ans} | composite={is_comp} | subs={sub_count}")
            if stem:
                print(f"    stem: {stem}")

        # OCR 原文前 30 行
        ocr = row['ocr_markdown']
        if ocr:
            lines = ocr.split('\n')
            print(f"\n=== OCR 原文前 30 行（共 {len(lines)} 行） ===")
            for i, line in enumerate(lines[:30]):
                print(f"  L{i+1:03d}: {line[:80]}")

    finally:
        await conn.close()

asyncio.run(main())

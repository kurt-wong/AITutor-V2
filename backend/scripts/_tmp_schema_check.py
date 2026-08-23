"""查 DB 中语文+英语的完整数据结构，确认验收脚本可用字段。"""
import asyncio, asyncpg, sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"

async def main():
    conn = await asyncpg.connect(DSN)
    try:
        # 查文档字段
        row = await conn.fetchrow("""
            SELECT id, filename, subject, 
                   LENGTH(ocr_markdown) as ocr_len,
                   LENGTH(native_markdown) as native_len,
                   LENGTH(llm_annotated_markdown) as l2_len
            FROM documents WHERE subject = '语文' LIMIT 1
        """)
        print(f"=== 语文文档 ===")
        print(f"  id: {row['id']}")
        print(f"  ocr_markdown: {row['ocr_len']} chars")
        print(f"  native_markdown: {row['native_len']} chars")
        print(f"  llm_annotated_markdown: {row['l2_len']} chars")

        # 查 L2 结构
        l2 = json.loads(row['l2_len'] and '[]' or '[]')
        # Actually let me fetch the real L2
        l2_raw = await conn.fetchval("""
            SELECT llm_annotated_markdown FROM documents WHERE subject = '语文' LIMIT 1
        """)
        if l2_raw:
            data = json.loads(l2_raw)
            q0 = data['questions'][0]
            print(f"\n  L2 question[0] keys: {list(q0.keys())}")

        # 查题目字段
        rows = await conn.fetch("""
            SELECT qi.source_question_number, q.stem, q.options, q.answer, 
                   q.is_composite, q.sub_questions, q.question_type_id,
                   q.source_document_name
            FROM questions q
            JOIN question_instances qi ON qi.question_id = q.id
            JOIN documents d ON d.id = qi.document_id
            WHERE d.subject = '语文'
            LIMIT 3
        """)
        print(f"\n  题目字段:")
        for r in rows:
            qn = r['source_question_number']
            print(f"    Q{qn}: stem_len={len(r['stem'] or '')}, options_type={type(r['options']).__name__}, answer_len={len(r['answer'] or '')}")

        # 英语同查
        row = await conn.fetchrow("""
            SELECT id, filename, subject,
                   LENGTH(ocr_markdown) as ocr_len,
                   LENGTH(native_markdown) as native_len,
                   LENGTH(llm_annotated_markdown) as l2_len
            FROM documents WHERE subject = '英语' LIMIT 1
        """)
        print(f"\n=== 英语文档 ===")
        print(f"  id: {row['id']}")
        print(f"  ocr_markdown: {row['ocr_len']} chars")
        print(f"  native_markdown: {row['native_len']} chars")
        print(f"  llm_annotated_markdown: {row['l2_len']} chars")

    finally:
        await conn.close()

asyncio.run(main())

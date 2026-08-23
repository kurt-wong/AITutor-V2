#!/usr/bin/env python3
import asyncio, asyncpg, json, sys, io
if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

async def main():
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:15432/aitutors")
    try:
        doc = await conn.fetchrow("""
            SELECT id, processing_status, ocr_markdown, llm_annotated_markdown
            FROM documents WHERE subject = '英语' ORDER BY created_at DESC LIMIT 1
        """)
        if not doc:
            print("No English doc")
            return
        print("Status:", doc["processing_status"])
        print("ocr_markdown len:", len(doc["ocr_markdown"] or ""))
        print("llm_annotated len:", len(doc["llm_annotated_markdown"] or ""))

        # L2 题数
        try:
            l2 = json.loads(doc["llm_annotated_markdown"] or "{}")
            print("L2 questions:", len(l2.get("questions", [])))
        except Exception as e:
            print("L2 parse error:", e)

        # DB 题数
        rows = await conn.fetch("""
            SELECT qi.source_question_number, q.stem, q.answer, q.is_composite
            FROM questions q
            JOIN question_instances qi ON qi.question_id = q.id
            WHERE qi.document_id = $1
            ORDER BY qi.source_question_number::int
        """, str(doc["id"]))
        print("DB questions:", len(rows))
        for r in rows:
            qn = r["source_question_number"]
            stem_len = len(r["stem"] or "")
            print(f"  Q{qn}: stem_len={stem_len} composite={r['is_composite']}")
    finally:
        await conn.close()

asyncio.run(main())

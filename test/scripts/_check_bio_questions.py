#!/usr/bin/env python3
import asyncio, asyncpg, sys, io
if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

async def main():
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:15432/aitutors")
    try:
        doc_id = "d67ce95f-b15e-426c-95e5-a5fd07a61573"
        rows = await conn.fetch("""
            SELECT qi.source_question_number, q.answer, q.status
            FROM questions q
            JOIN question_instances qi ON qi.question_id = q.id
            WHERE qi.document_id = $1
            ORDER BY qi.source_question_number::int
        """, doc_id)
        print("Questions in DB:", len(rows))
        for row in rows:
            qn = row["source_question_number"]
            ans = row["answer"]
            status = row["status"]
            print("  Q" + str(qn) + ": answer=" + repr(ans) + " status=" + str(status))
    finally:
        await conn.close()

asyncio.run(main())

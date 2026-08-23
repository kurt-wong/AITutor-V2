#!/usr/bin/env python3
"""清理英语学科 DB 数据，为重跑入库做准备。"""
import sys, io, asyncio
if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

async def main():
    import asyncpg
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:15432/aitutors")
    try:
        # 找英语文档
        doc = await conn.fetchrow("""
            SELECT id, filename FROM documents
            WHERE subject = '英语' AND processing_status = 'completed'
            ORDER BY created_at DESC LIMIT 1
        """)
        if not doc:
            print("No English doc found")
            return

        doc_id = str(doc["id"])
        print("Clearing:", doc["filename"][:60])
        print("Doc ID:", doc_id)

        # 1. question_knowledge
        await conn.execute("""
            DELETE FROM question_knowledge WHERE question_id IN (
                SELECT q.id FROM questions q
                JOIN question_instances qi ON qi.question_id = q.id
                WHERE qi.document_id = $1
            )
        """, doc_id)
        # 2. question_embeddings
        await conn.execute("""
            DELETE FROM question_embeddings WHERE question_id IN (
                SELECT q.id FROM questions q
                JOIN question_instances qi ON qi.question_id = q.id
                WHERE qi.document_id = $1
            )
        """, doc_id)
        # 3. question_images
        await conn.execute("""
            DELETE FROM question_images WHERE question_id IN (
                SELECT q.id FROM questions q
                JOIN question_instances qi ON qi.question_id = q.id
                WHERE qi.document_id = $1
            )
        """, doc_id)
        # 4. question_instances
        await conn.execute("DELETE FROM question_instances WHERE document_id = $1", doc_id)
        # 5. orphan questions
        await conn.execute("""
            DELETE FROM questions WHERE id NOT IN (
                SELECT DISTINCT question_id FROM question_instances
            )
        """)
        # 6. tasks + logs
        await conn.execute("DELETE FROM background_tasks WHERE payload_json->>'document_id' = $1", doc_id)
        await conn.execute("DELETE FROM document_processing_logs WHERE document_id = $1", doc_id)
        # 7. document
        await conn.execute("DELETE FROM documents WHERE id = $1", doc_id)

        count = await conn.fetchval("SELECT COUNT(*) FROM documents WHERE subject = '英语'")
        print("English docs remaining:", count)
        print("Clean. Ready for re-upload.")

    finally:
        await conn.close()

asyncio.run(main())

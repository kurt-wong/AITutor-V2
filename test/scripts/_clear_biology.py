#!/usr/bin/env python3
"""清理生物学科 DB 数据，为重跑入库做准备。"""
import sys
import io
import asyncio
if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

async def main():
    import asyncpg
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:15432/aitutors")
    try:
        # Find biology document
        doc = await conn.fetchrow("""
            SELECT id, filename FROM documents
            WHERE subject = '生物' AND processing_status = 'completed'
            ORDER BY created_at DESC LIMIT 1
        """)
        if not doc:
            print("No biology doc found")
            return

        doc_id = str(doc["id"])
        print(f"Clearing biology data for: {doc['filename']}")
        print(f"Document ID: {doc_id}")

        # Count before
        q_count = await conn.fetchval("""
            SELECT COUNT(*) FROM questions q
            JOIN question_instances qi ON qi.question_id = q.id
            WHERE qi.document_id = $1
        """, doc_id)
        print(f"Questions to delete: {q_count}")

        # Delete in FK order
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
        await conn.execute("""
            DELETE FROM question_instances WHERE document_id = $1
        """, doc_id)

        # 5. questions (only if no other instances)
        orphan_questions = await conn.fetch("""
            SELECT q.id FROM questions q
            LEFT JOIN question_instances qi ON qi.question_id = q.id
            WHERE qi.id IS NULL
        """)
        if orphan_questions:
            await conn.execute("""
                DELETE FROM questions WHERE id = ANY($1)
            """, [r["id"] for r in orphan_questions])
            print(f"Deleted {len(orphan_questions)} orphan questions")

        # 6. Reset document status
        await conn.execute("""
            UPDATE documents SET processing_status = 'pending'
            WHERE id = $1
        """, doc_id)

        # 7. Delete background tasks
        await conn.execute("""
            DELETE FROM background_tasks
            WHERE payload_json->>'document_id' = $1
        """, doc_id)

        # Verify
        remaining = await conn.fetchval("""
            SELECT COUNT(*) FROM question_instances WHERE document_id = $1
        """, doc_id)
        print(f"Remaining instances: {remaining}")
        print("Biology data cleared. Ready for re-upload.")

    finally:
        await conn.close()

asyncio.run(main())

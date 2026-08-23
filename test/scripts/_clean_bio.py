#!/usr/bin/env python3
"""清理生物旧数据 + 新数据，重跑入库，验证 Q6/Q7。"""
import sys, io, asyncio, json
if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

async def main():
    import asyncpg
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:15432/aitutors")
    try:
        # 1. 删除新上传的文档（2822831a）
        new_doc_id = "2822831a-0281-40c9-a622-99200cd2c2ef"
        old_doc_id = "d67ce95f-b15e-426c-95e5-a5fd07a61573"
        
        for doc_id in [new_doc_id, old_doc_id]:
            # Delete FK dependents
            await conn.execute("""
                DELETE FROM question_knowledge WHERE question_id IN (
                    SELECT q.id FROM questions q
                    JOIN question_instances qi ON qi.question_id = q.id
                    WHERE qi.document_id = $1
                )
            """, doc_id)
            await conn.execute("""
                DELETE FROM question_embeddings WHERE question_id IN (
                    SELECT q.id FROM questions q
                    JOIN question_instances qi ON qi.question_id = q.id
                    WHERE qi.document_id = $1
                )
            """, doc_id)
            await conn.execute("""
                DELETE FROM question_images WHERE question_id IN (
                    SELECT q.id FROM questions q
                    JOIN question_instances qi ON qi.question_id = q.id
                    WHERE qi.document_id = $1
                )
            """, doc_id)
            await conn.execute("DELETE FROM question_instances WHERE document_id = $1", doc_id)
            await conn.execute("""
                DELETE FROM questions WHERE id NOT IN (
                    SELECT DISTINCT question_id FROM question_instances
                )
            """)
            await conn.execute("DELETE FROM background_tasks WHERE payload_json->>'document_id' = $1", doc_id)
            await conn.execute("DELETE FROM document_processing_logs WHERE document_id = $1", doc_id)
        
        # Delete documents
        await conn.execute("DELETE FROM documents WHERE id IN ($1, $2)", new_doc_id, old_doc_id)
        
        # Verify clean
        count = await conn.fetchval("SELECT COUNT(*) FROM documents WHERE subject = '生物'")
        print("Biology documents remaining:", count)
        print("Clean. Ready for re-upload.")

    finally:
        await conn.close()

asyncio.run(main())

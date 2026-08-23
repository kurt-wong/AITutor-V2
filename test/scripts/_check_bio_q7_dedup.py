#!/usr/bin/env python3
"""检查生物 Q7 是否因 content_hash 去重导致答案未更新。"""
import sys
import io
import asyncio
import json
if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

async def main():
    import asyncpg
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:15432/aitutors")
    try:
        # Find all biology documents
        docs = await conn.fetch("""
            SELECT id, filename, created_at
            FROM documents
            WHERE subject = '生物' AND processing_status = 'completed'
            ORDER BY created_at
        """)
        print(f"Biology documents: {len(docs)}")
        for doc in docs:
            print(f"  {doc['id']}: {doc['filename']} ({doc['created_at']})")

        # Find all Q7 questions across biology documents
        for doc in docs:
            doc_id = str(doc["id"])
            rows = await conn.fetch("""
                SELECT q.id, q.answer, q.content_hash, q.created_at,
                       qi.source_question_number, qi.document_id
                FROM questions q
                JOIN question_instances qi ON qi.question_id = q.id
                WHERE qi.document_id = $1 AND qi.source_question_number = '7'
            """, doc_id)
            for row in rows:
                print(f"\n  Q7 in doc {doc_id[:8]}:")
                print(f"    answer: {repr(row['answer'])}")
                print(f"    content_hash: {repr(row['content_hash'][:20] if row['content_hash'] else None)}")
                print(f"    created_at: {row['created_at']}")

        # Check how many instances Q7 has
        q7_rows = await conn.fetch("""
            SELECT q.id, q.answer, q.content_hash, q.created_at,
                   COUNT(qi.id) as instance_count
            FROM questions q
            JOIN question_instances qi ON qi.question_id = q.id
            JOIN documents d ON qi.document_id = d.id
            WHERE d.subject = '生物' AND qi.source_question_number = '7'
            GROUP BY q.id, q.answer, q.content_hash, q.created_at
        """)
        print(f"\n=== Q7 questions with instance count ===")
        for row in q7_rows:
            print(f"  Q_id={str(row['id'])[:8]}: answer={repr(row['answer'])}, instances={row['instance_count']}, created={row['created_at']}")

    finally:
        await conn.close()

asyncio.run(main())

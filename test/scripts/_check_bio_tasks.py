#!/usr/bin/env python3
"""检查生物文档的所有 task 及其结果。"""
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
        doc = await conn.fetchrow("""
            SELECT id, filename FROM documents
            WHERE subject = '生物' AND processing_status = 'completed'
            ORDER BY created_at DESC LIMIT 1
        """)
        doc_id = str(doc["id"])
        print(f"Doc: {doc['filename']}")

        # Find all tasks
        tasks = await conn.fetch("""
            SELECT id, status, created_at, result_json
            FROM background_tasks
            WHERE payload_json->>'document_id' = $1
            ORDER BY created_at
        """, doc_id)
        print(f"Tasks: {len(tasks)}")
        
        for task in tasks:
            print(f"\n  Task {str(task['id'])[:8]}: status={task['status']}, created={task['created_at']}")
            result = task["result_json"]
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except:
                    result = {}
            
            questions = result.get("questions", [])
            for q in questions:
                if isinstance(q, dict) and str(q.get("question_number")) == "7":
                    print(f"    Q7: answer={repr(q.get('answer'))}, provenance={q.get('answer_provenance')}")

    finally:
        await conn.close()

asyncio.run(main())

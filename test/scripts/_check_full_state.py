#!/usr/bin/env python3
import asyncio, asyncpg, sys, io, json
if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

async def main():
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:15432/aitutors")
    try:
        rows = await conn.fetch("""
            SELECT id, filename, subject, processing_status, created_at
            FROM documents ORDER BY created_at DESC LIMIT 5
        """)
        print("Recent documents:")
        for row in rows:
            print(" ", str(row["id"])[:8], row["subject"], row["processing_status"], str(row["created_at"])[:19])

        # Check task result
        task = await conn.fetchrow("""
            SELECT id, status, result_json FROM background_tasks
            ORDER BY created_at DESC LIMIT 1
        """)
        if task:
            print("\nLatest task:", str(task["id"])[:8], task["status"])
            result = task["result_json"]
            if isinstance(result, str):
                try: result = json.loads(result)
                except: result = {}
            if isinstance(result, dict):
                qs = result.get("questions", [])
                print("Questions in task result:", len(qs))
                for q in qs:
                    if isinstance(q, dict):
                        qno = str(q.get("question_number", ""))
                        if qno in ["6", "7"]:
                            print("  Q" + qno + ": answer=" + repr(q.get("answer")))
            # Get document_id from task
            payload = await conn.fetchrow("""
                SELECT payload_json FROM background_tasks WHERE id = $1
            """, task["id"])
            if payload:
                p = payload["payload_json"]
                if isinstance(p, str):
                    try: p = json.loads(p)
                    except: p = {}
                doc_id = p.get("document_id")
                print("Task document_id:", doc_id)
                
                if doc_id:
                    q_rows = await conn.fetch("""
                        SELECT qi.source_question_number, q.answer
                        FROM questions q
                        JOIN question_instances qi ON qi.question_id = q.id
                        WHERE qi.document_id = $1
                        ORDER BY qi.source_question_number::int
                    """, doc_id)
                    print("Questions in DB for this doc:", len(q_rows))
                    for qr in q_rows:
                        qn = qr["source_question_number"]
                        if str(qn) in ["6", "7"]:
                            print("  Q" + str(qn) + ": DB answer=" + repr(qr["answer"]))

    finally:
        await conn.close()

asyncio.run(main())

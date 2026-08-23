#!/usr/bin/env python3
import asyncio, asyncpg, json, sys, io
if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

async def main():
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:15432/aitutors")
    try:
        task = await conn.fetchrow("""
            SELECT id, status, result_json FROM background_tasks
            ORDER BY created_at DESC LIMIT 1
        """)
        if task:
            print("Task:", str(task["id"])[:8], "status:", task["status"])
            result = task["result_json"]
            if isinstance(result, str):
                try: result = json.loads(result)
                except: result = {}
            if isinstance(result, dict):
                qs = result.get("questions", [])
                print("Questions:", len(qs))
                for q in qs:
                    if isinstance(q, dict):
                        qno = str(q.get("question_number", ""))
                        if qno in ["6", "7"]:
                            print("  Q" + qno + ": answer=" + repr(q.get("answer")))
            
            # Check DB
            payload = task.get("result_json")
            p = await conn.fetchrow("SELECT payload_json FROM background_tasks WHERE id = $1", task["id"])
            if p:
                pp = p["payload_json"]
                if isinstance(pp, str):
                    try: pp = json.loads(pp)
                    except: pp = {}
                doc_id = pp.get("document_id")
                if doc_id:
                    for qn in ["6", "7"]:
                        row = await conn.fetchrow("""
                            SELECT q.answer FROM questions q
                            JOIN question_instances qi ON qi.question_id = q.id
                            WHERE qi.document_id = $1 AND qi.source_question_number = $2
                        """, doc_id, qn)
                        if row:
                            print("  Q" + qn + " DB: answer=" + repr(row["answer"]))
        else:
            print("No task found")
    finally:
        await conn.close()

asyncio.run(main())

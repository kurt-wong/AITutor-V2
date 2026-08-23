#!/usr/bin/env python3
import asyncio, asyncpg, json, sys, io
if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

async def main():
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:15432/aitutors")
    try:
        row = await conn.fetchrow("""
            SELECT id, status, created_at, result_json
            FROM background_tasks WHERE id = $1
        """, "6b61c167-07ce-410a-8a7e-6c85e99bdf62")
        if row:
            print("Status:", row["status"])
            print("Created:", row["created_at"])
            result = row["result_json"]
            if isinstance(result, str):
                try: result = json.loads(result)
                except: pass
            if isinstance(result, dict):
                qs = result.get("questions", [])
                print("Questions:", len(qs))
                for q in qs:
                    if isinstance(q, dict):
                        qno = str(q.get("question_number", ""))
                        if qno in ["6", "7"]:
                            print("  Q" + qno + ": answer=" + repr(q.get("answer")))
        else:
            print("Task not found")
    finally:
        await conn.close()

asyncio.run(main())

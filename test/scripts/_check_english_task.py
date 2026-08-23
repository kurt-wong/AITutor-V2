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
            if task["status"] in ("succeeded", "failed"):
                result = task["result_json"]
                if isinstance(result, str):
                    try: result = json.loads(result)
                    except: result = {}
                if isinstance(result, dict):
                    qs = result.get("questions", [])
                    print("Questions:", len(qs))
                    # Check composite material
                    for q in qs:
                        if isinstance(q, dict):
                            qno = str(q.get("question_number", ""))
                            if qno in ["26", "27", "28"]:
                                mat = q.get("shared_material") or ""
                                stem = q.get("stem") or ""
                                print("  Q" + qno + ": shared_material_len=" + str(len(mat)) + " stem_len=" + str(len(stem)))
        else:
            print("No task")
    finally:
        await conn.close()

asyncio.run(main())

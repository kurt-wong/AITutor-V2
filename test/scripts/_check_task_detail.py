#!/usr/bin/env python3
"""查当前英语任务详细进度。"""
import asyncio, asyncpg, json, sys, io
if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

async def main():
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:15432/aitutors")
    try:
        task = await conn.fetchrow("""
            SELECT id, status, result_json, updated_at
            FROM background_tasks ORDER BY created_at DESC LIMIT 1
        """)
        print("Task:", str(task["id"])[:8], "status:", task["status"])
        print("Updated:", task["updated_at"])
        result = task["result_json"]
        if isinstance(result, str):
            try: result = json.loads(result)
            except: result = {}
        if isinstance(result, dict):
            print("Result keys:", list(result.keys())[:20])
            if "stage_errors" in result:
                print("Stage errors:", result["stage_errors"])
            if "progress" in result:
                print("Progress:", result["progress"])
    finally:
        await conn.close()

asyncio.run(main())

#!/usr/bin/env python3
import asyncio, asyncpg, json, sys, io
if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

async def main():
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:15432/aitutors")
    try:
        rows = await conn.fetch("""
            SELECT id, status, created_at, updated_at
            FROM background_tasks ORDER BY created_at DESC LIMIT 5
        """)
        for r in rows:
            print("Task:", str(r["id"])[:8], "status:", r["status"], "created:", r["created_at"], "updated:", r["updated_at"])
    finally:
        await conn.close()

asyncio.run(main())

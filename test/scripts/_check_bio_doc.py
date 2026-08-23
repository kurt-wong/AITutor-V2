#!/usr/bin/env python3
import asyncio, asyncpg, sys, io
if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

async def main():
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:15432/aitutors")
    try:
        rows = await conn.fetch("""
            SELECT id, filename, subject, processing_status
            FROM documents WHERE subject = '生物'
            ORDER BY created_at DESC
        """)
        print("Biology documents:", len(rows))
        for row in rows:
            print(" ", str(row["id"])[:8], row["processing_status"], row["filename"][:50])
        
        # Check task
        task = await conn.fetchrow("""
            SELECT id, status FROM background_tasks
            ORDER BY created_at DESC LIMIT 1
        """)
        if task:
            print("Latest task:", str(task["id"])[:8], task["status"])
    finally:
        await conn.close()

asyncio.run(main())

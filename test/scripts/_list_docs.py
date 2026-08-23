#!/usr/bin/env python3
import sys, io, asyncio
if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

async def main():
    import asyncpg
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:15432/aitutors")
    try:
        rows = await conn.fetch("""
            SELECT id, filename, subject, processing_status
            FROM documents ORDER BY created_at DESC LIMIT 10
        """)
        for row in rows:
            fn = row["filename"] or ""
            subj = row["subject"] or "NULL"
            print(str(row["id"])[:8], "|", subj, "|", row["processing_status"], "|", fn[:40])
    finally:
        await conn.close()

asyncio.run(main())

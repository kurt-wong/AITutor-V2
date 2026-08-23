#!/usr/bin/env python3
import asyncio, asyncpg, sys, io
if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

async def main():
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:15432/aitutors")
    try:
        # 找到 subject 为 NULL 的文档（生物）
        rows = await conn.fetch("""
            SELECT id, filename FROM documents
            WHERE subject IS NULL OR subject = ''
        """)
        for row in rows:
            fn = row["filename"] or ""
            if "生物" in fn or "%E7%94%9F%E7%89%A9" in fn:
                await conn.execute(
                    "UPDATE documents SET subject = '生物' WHERE id = $1",
                    str(row["id"]),
                )
                print("Fixed subject for:", fn[:50])
            else:
                print("Unknown subject NULL doc:", fn[:50])

        # Verify
        bio = await conn.fetchrow("""
            SELECT subject FROM documents WHERE filename LIKE '%生物%'
            ORDER BY created_at DESC LIMIT 1
        """)
        if bio:
            print("Biology subject now:", bio["subject"])
    finally:
        await conn.close()

asyncio.run(main())

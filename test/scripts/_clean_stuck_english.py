#!/usr/bin/env python3
"""清理卡住的英语 task 和文档。"""
import sys, io, asyncio
if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

async def main():
    import asyncpg
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:15432/aitutors")
    try:
        # 找卡住的英语文档（2083adda）
        doc_id = "2083adda-a126-44ae-bd1d-ab4c95fbe2b3"
        await conn.execute("DELETE FROM background_tasks WHERE payload_json->>'document_id' = $1", doc_id)
        await conn.execute("DELETE FROM document_processing_logs WHERE document_id = $1", doc_id)
        await conn.execute("DELETE FROM documents WHERE id = $1", doc_id)
        print("Cleaned stuck task/doc")

        count = await conn.fetchval("SELECT COUNT(*) FROM documents WHERE subject = '英语'")
        print("English docs:", count)
    finally:
        await conn.close()

asyncio.run(main())

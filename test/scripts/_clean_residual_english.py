#!/usr/bin/env python3
"""清理残留的英语 processing 文档。"""
import sys, io, asyncio
if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

async def main():
    import asyncpg
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:15432/aitutors")
    try:
        # 清理所有 subject 为 NULL 且文件名含英语的 processing 文档
        rows = await conn.fetch("""
            SELECT id, filename FROM documents
            WHERE processing_status = 'processing' OR (subject IS NULL AND filename LIKE '%%英语%%')
        """)
        for row in rows:
            doc_id = str(row["id"])
            print("Cleaning:", doc_id[:8], row["filename"][:40])
            await conn.execute("DELETE FROM background_tasks WHERE payload_json->>'document_id' = $1", doc_id)
            await conn.execute("DELETE FROM document_processing_logs WHERE document_id = $1", doc_id)
            await conn.execute("DELETE FROM documents WHERE id = $1", doc_id)
        print("Done. Remaining english docs:", await conn.fetchval("SELECT COUNT(*) FROM documents WHERE filename LIKE '%%英语%%'"))
    finally:
        await conn.close()

asyncio.run(main())

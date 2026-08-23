#!/usr/bin/env python3
"""查英语文档状态和 OCR 阶段。"""
import asyncio, asyncpg, json, sys, io
if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

async def main():
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:15432/aitutors")
    try:
        doc = await conn.fetchrow("""
            SELECT id, filename, processing_status, ocr_markdown, native_markdown, created_at
            FROM documents WHERE subject = '英语'
            ORDER BY created_at DESC LIMIT 1
        """)
        if doc:
            print("Doc:", str(doc["id"])[:8], "status:", doc["processing_status"])
            print("Created:", doc["created_at"])
            print("ocr_markdown len:", len(doc["ocr_markdown"] or ""))
            print("native_markdown len:", len(doc["native_markdown"] or ""))
        else:
            print("No English doc")

        # 看 processing logs 表结构
        cols = await conn.fetch("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'document_processing_logs' ORDER BY ordinal_position
        """)
        print("\ndocument_processing_logs columns:", [c["column_name"] for c in cols])
    finally:
        await conn.close()

asyncio.run(main())

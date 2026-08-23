#!/usr/bin/env python3
"""检查生物 L1 答案表行的来源。"""
import sys, io, asyncio, json
if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

async def main():
    import asyncpg
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:15432/aitutors")
    try:
        doc = await conn.fetchrow("""
            SELECT id, filename, native_markdown, ocr_markdown FROM documents
            WHERE subject = '生物' OR filename LIKE '%生物%'
            ORDER BY created_at DESC LIMIT 1
        """)
        if not doc:
            print("No biology doc")
            return

        print("Doc:", doc["filename"][:60])
        print("subject:", doc["subject"])

        native = doc["native_markdown"] or ""
        ocr = doc["ocr_markdown"] or ""

        # Find answer table in native
        import re
        n_idx = native.find("参考答案")
        if n_idx >= 0:
            n_section = native[n_idx:]
            n_lines = n_section.split("\n")
            print("\n=== Native answer section (first 25 lines) ===")
            for i, line in enumerate(n_lines[:25]):
                print(f"  N{i}: {repr(line[:60])}")

        o_idx = ocr.find("参考答案")
        if o_idx >= 0:
            o_section = ocr[o_idx:]
            print("\n=== OCR answer section (first 300 chars) ===")
            print(repr(o_section[:300]))

    finally:
        await conn.close()

asyncio.run(main())

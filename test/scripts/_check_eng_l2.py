#!/usr/bin/env python3
import asyncio, asyncpg, json, sys, io
if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

async def main():
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:15432/aitutors")
    try:
        doc = await conn.fetchrow("""
            SELECT id, ocr_markdown, llm_annotated_markdown
            FROM documents WHERE subject = '英语' ORDER BY created_at DESC LIMIT 1
        """)
        l2 = json.loads(doc["llm_annotated_markdown"] or "{}")
        qs = l2.get("questions", [])
        print("L2 questions:", len(qs))
        for q in qs:
            qno = q.get("question_number")
            is_comp = q.get("is_composite")
            stem_ids = len(q.get("stem_line_ids") or [])
            mat_ids = len(q.get("shared_material_line_ids") or [])
            ans = (q.get("answer") or "")[:30]
            print(f"  Q{qno}: comp={is_comp} stem_lines={stem_ids} mat_lines={mat_ids} ans={ans!r}")

        # OCR markdown 前 500 字符
        ocr = doc["ocr_markdown"] or ""
        print("\n=== OCR markdown first 500 ===")
        print(ocr[:500])
    finally:
        await conn.close()

asyncio.run(main())

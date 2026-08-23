#!/usr/bin/env python3
"""检查生物 OCR 答案表解析结果。"""
import sys
import io
import re
import asyncio
if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

async def main():
    import asyncpg
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:15432/aitutors")
    try:
        row = await conn.fetchrow("""
            SELECT ocr_markdown FROM documents
            WHERE subject = '生物' AND processing_status = 'completed'
            ORDER BY created_at DESC LIMIT 1
        """)
        ocr = row["ocr_markdown"] or ""
        
        # Find answer section
        idx = ocr.find("参考答案")
        if idx < 0:
            print("NO answer section in OCR")
            return
        
        section = ocr[idx:]
        print("=== OCR answer section (first 800 chars) ===")
        print(section[:800])
        
        # Parse the text table format
        lines = section.split("\n")
        print(f"\n=== Line-by-line (first 30) ===")
        for i, line in enumerate(lines[:30]):
            print(f"  L{i}: {repr(line[:80])}")
        
        # Try to parse as answer table
        # Look for "题号" followed by numbers, then "答案" followed by answers
        qnums = []
        answers = []
        for i, line in enumerate(lines[:30]):
            line = line.strip()
            if line == "题号":
                qnums = []
            elif line == "答案":
                answers = []
            elif line.isdigit() and not answers:
                qnums.append(line)
            elif line and not line.isdigit() and qnums and len(answers) < len(qnums):
                answers.append(line)
        
        print(f"\n=== Parsed table ===")
        print(f"Qnums: {qnums}")
        print(f"Answers: {answers}")
        for qn, ans in zip(qnums, answers):
            print(f"  Q{qn}: {ans}")

    finally:
        await conn.close()

asyncio.run(main())

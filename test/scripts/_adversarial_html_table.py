#!/usr/bin/env python3
"""对抗性审查：检查化学/政治/生物的 HTML 表格结构。"""
import asyncio
import json
import re
import sys
import io

if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"

async def main():
    import asyncpg
    conn = await asyncpg.connect(DSN)
    try:
        for subject in ["化学", "政治", "生物"]:
            doc = await conn.fetchrow(
                "SELECT id, filename, native_markdown, ocr_markdown "
                "FROM documents WHERE subject=$1 AND processing_status='completed' "
                "ORDER BY created_at DESC LIMIT 1",
                subject,
            )
            if not doc:
                continue

            source = doc["ocr_markdown"] or doc["native_markdown"] or ""
            
            # Find answer section
            answer_match = re.search("参考答案", source)
            if not answer_match:
                print(f"{subject}: NO '参考答案' found")
                continue
            
            answer_section = source[answer_match.start():]
            print(f"\n=== {subject} ===")
            print(f"Answer section length: {len(answer_section)} chars")
            
            # Find HTML tables
            tables = re.findall(r"<table>.*?</table>", answer_section, re.DOTALL)
            print(f"HTML tables found: {len(tables)}")
            
            if tables:
                for i, table in enumerate(tables[:2]):
                    print(f"\nTable {i+1} ({len(table)} chars):")
                    print(f"  First 300 chars: {repr(table[:300])}")
                    
                    # Parse rows
                    rows = re.findall(r"<tr>(.*?)</tr>", table, re.DOTALL)
                    print(f"  Rows: {len(rows)}")
                    for j, row in enumerate(rows[:3]):
                        tds = re.findall(r"<td>(.*?)</td>", row)
                        print(f"  Row {j}: {tds[:5]}...")
            
            # Also check for answer markers without HTML table
            answer_markers = re.findall(r"【答案】", answer_section)
            print(f"\n【答案】 markers: {len(answer_markers)}")
            
            # Check for inline answer format
            inline_matches = re.findall(r"(\d+)\s*[.．]\s*([A-D]{1,4})", answer_section[:1000])
            print(f"Inline answers (first 1000 chars): {inline_matches[:10]}")

    finally:
        await conn.close()

asyncio.run(main())

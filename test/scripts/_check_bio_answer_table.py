#!/usr/bin/env python3
"""检查生物答案表解析结果。"""
import sys
import io
import re
if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import fitz

# Read PDF directly
pdf_path = r"test/pdf/2026北京北师大附中高一（上）期末生物（教师版）.pdf"
doc = fitz.open(pdf_path)
pdf_text = ""
for page in doc:
    pdf_text += page.get_text("text")
doc.close()

# Find answer section
idx = pdf_text.find("参考答案")
if idx < 0:
    print("NO answer section in PDF")
else:
    section = pdf_text[idx:]
    print("=== PDF answer section (first 600 chars) ===")
    print(section[:600])

# Parse the table manually
lines = section.split("\n")
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

# Now check what answer_matcher would produce
# Parse HTML table from OCR
import asyncpg

async def check_ocr():
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:15432/aitutors")
    try:
        row = await conn.fetchrow("""
            SELECT ocr_markdown FROM documents
            WHERE subject = '生物' AND processing_status = 'completed'
            ORDER BY created_at DESC LIMIT 1
        """)
        ocr = row["ocr_markdown"] or ""
        
        # Find HTML table
        table_match = re.search(r"<table>.*?</table>", ocr, re.DOTALL)
        if table_match:
            table_text = table_match.group(0)
            print(f"\n=== OCR HTML table ===")
            print(table_text[:500])
            
            # Parse it
            rows = re.findall(r"<tr>(.*?)</tr>", table_text, re.DOTALL)
            for i, row_text in enumerate(rows):
                tds = [t.strip() for t in re.findall(r"<td>(.*?)</td>", row_text)]
                print(f"  Row {i}: {tds}")
    finally:
        await conn.close()

import asyncio
asyncio.run(check_ocr())

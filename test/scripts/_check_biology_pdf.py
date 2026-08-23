#!/usr/bin/env python3
"""独立复核：生物 PDF 原始文本中的答案表。"""
import sys
import io
if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import fitz
pdf_path = r"test/pdf/2026北京北师大附中高一（上）期末生物（教师版）.pdf"
doc = fitz.open(pdf_path)
text = ""
for page in doc:
    text += page.get_text("text")
doc.close()

idx = text.find("参考答案")
if idx < 0:
    print("NO answer section found")
else:
    section = text[idx:]
    print("=== PDF raw text (answer section, first 800 chars) ===")
    print(section[:800])
    print("\n=== Table parsing ===")
    lines = section.split("\n")
    for i, line in enumerate(lines[:30]):
        print(f"  L{i}: {repr(line[:80])}")

# Now verify Q6 and Q7 specifically
print("\n=== Q6 and Q7 verification ===")
# Find the answer table
table_started = False
qnums = []
answers = []
for line in lines:
    line = line.strip()
    if line.startswith("题号"):
        table_started = True
        qnums = []
        answers = []
        continue
    if table_started and line.startswith("答案"):
        table_started = False
        continue
    if table_started and line.isdigit():
        qnums.append(line)
        continue
    if not table_started and qnums and not answers:
        # We have qnums but no answers yet - this line should be answers
        if line and line[0].isalpha():
            answers.append(line)

print(f"  Qnums: {qnums}")
print(f"  Answers: {answers}")
if len(qnums) >= 6 and len(answers) >= 6:
    print(f"  Q6: PDF='{qnums[5] if len(qnums) > 5 else 'N/A'}' -> Answer='{answers[5] if len(answers) > 5 else 'N/A'}'")
    print(f"  Q7: PDF='{qnums[6] if len(qnums) > 6 else 'N/A'}' -> Answer='{answers[6] if len(answers) > 6 else 'N/A'}'")

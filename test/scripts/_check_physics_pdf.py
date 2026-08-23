#!/usr/bin/env python3
"""独立复核：物理 PDF 原始文本中的答案表。"""
import sys
import io
if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import fitz
pdf_path = r"test/pdf/2026北京八十中高一（上）期末物理（教师版）.pdf"
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
    print("=== PDF raw text (answer section, first 1500 chars) ===")
    print(section[:1500])
    print("\n=== Table parsing ===")
    lines = section.split("\n")
    for i, line in enumerate(lines[:20]):
        print(f"  L{i}: {repr(line[:100])}")

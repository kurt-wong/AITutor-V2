#!/usr/bin/env python3
"""独立复核：历史 PDF 原始文本中的内联答案。"""
import sys
import io
import re
if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import fitz
pdf_path = r"test/pdf/2025北京东城高一（上）期末历史（教师版）.pdf"
doc = fitz.open(pdf_path)
text = ""
for page in doc:
    text += page.get_text("text")
doc.close()

# Check for answer section
idx = text.find("参考答案")
if idx >= 0:
    print("=== Found '参考答案' ===")
    section = text[idx:]
    print(section[:500])
else:
    print("=== No '参考答案' found ===")

# Check for inline answer patterns
print("\n=== Inline answer patterns ===")
patterns = [
    (r"故选([A-D])项", "故选X项"),
    (r"答案[：:]\s*([A-D])", "答案：X"),
    (r"答案为([A-D])", "答案为X"),
    (r"选([A-D])", "选X"),
]

for regex, desc in patterns:
    matches = list(re.finditer(regex, text))
    if matches:
        print(f"\n  Pattern '{desc}': {len(matches)} matches")
        for m in matches[:10]:
            # Find the question number context
            start = max(0, m.start() - 50)
            context = text[start:m.end() + 10].replace("\n", " ")
            print(f"    @{m.start()}: ...{context[:80]}...")

# Also check for Q1-Q40 answers
print("\n=== Looking for question-specific answers ===")
for qn in range(1, 41):
    # Try to find answer for this question
    patterns_for_qn = [
        rf"{qn}\s*[.．]\s*.*?故选([A-D])项",
        rf"^{qn}\s*[.．].*?答案[：:]\s*([A-D])",
    ]
    for regex in patterns_for_qn:
        m = re.search(regex, text, re.MULTILINE | re.DOTALL)
        if m:
            print(f"  Q{qn}: {m.group(1)} (from '{regex[:30]}...')")
            break

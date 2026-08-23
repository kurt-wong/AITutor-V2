#!/usr/bin/env python3
"""重跑全部 9 科答案验证。"""
import sys, io, asyncio, json, re
if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import fitz

DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"
PDF_DIR = r"test/pdf"

def extract_answer_section(text):
    if not text:
        return ""
    for pattern in ["参考答案", "答案[：:]", r"Answer\s*Key", "【答案】"]:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return text[m.start():]
    return ""

def parse_native_table(text):
    answers = {}
    lines = text.split("\n")
    i = 0
    while i < len(lines) - 1:
        line = lines[i].strip()
        next_line = lines[i + 1].strip()
        if line.startswith("题号") and next_line.startswith("答案"):
            qnums = line[2:].strip().split()
            ans_list = next_line[2:].strip().split()
            for qn, ans in zip(qnums, ans_list):
                if qn.isdigit():
                    answers[qn] = ans.strip()
            i += 2
        else:
            i += 1
    return answers

def parse_inline(text):
    answers = {}
    for m in re.finditer(r"(\d+)\s*[.．]\s*([A-D]{1,4})", text):
        qn = m.group(1)
        if qn not in answers:
            answers[qn] = m.group(2)
    return answers

def compact(text):
    if not text:
        return ""
    out = []
    for ch in str(text):
        code = ord(ch)
        if ch in "\u2018\u2019": out.append("'"); continue
        if ch in "\u201c\u201d": out.append('"'); continue
        if ch == "\u3000": continue
        if 0xFF01 <= code <= 0xFF5E: out.append(chr(code - 0xFEE0)); continue
        if ch.isspace(): continue
        out.append(ch)
    return "".join(out)

async def main():
    import asyncpg
    conn = await asyncpg.connect(DSN)
    try:
        docs = await conn.fetch("""
            SELECT id, filename, subject FROM documents
            WHERE processing_status = 'completed' ORDER BY subject
        """)
        
        total_matched = 0
        total_mismatched = 0
        total_unverifiable = 0
        all_mismatches = []
        
        for doc in docs:
            subject = doc["subject"]
            doc_id = str(doc["id"])
            filename = doc["filename"] or ""
            
            # Find PDF
            import urllib.parse
            decoded = urllib.parse.unquote(filename)
            import os
            pdf_path = os.path.join(PDF_DIR, decoded)
            if not os.path.exists(pdf_path):
                continue
            
            # Read PDF
            pdf_doc = fitz.open(pdf_path)
            pdf_text = ""
            for page in pdf_doc:
                pdf_text += page.get_text("text")
            pdf_doc.close()
            
            pdf_section = extract_answer_section(pdf_text)
            pdf_answers = {**parse_native_table(pdf_section), **parse_inline(pdf_section)}
            
            # Get DB answers
            db_rows = await conn.fetch("""
                SELECT qi.source_question_number, q.answer
                FROM questions q
                JOIN question_instances qi ON qi.question_id = q.id
                WHERE qi.document_id = $1
                ORDER BY qi.source_question_number::int
            """, doc_id)
            
            matched = 0
            mismatched = 0
            unverifiable = 0
            
            for row in db_rows:
                qn = str(row["source_question_number"])
                db_ans = (row["answer"] or "").strip()
                pdf_ans = pdf_answers.get(qn)
                
                if not pdf_ans:
                    unverifiable += 1
                    continue
                
                db_norm = compact(db_ans).upper()
                pdf_norm = compact(pdf_ans).upper()
                
                if db_norm == pdf_norm:
                    matched += 1
                else:
                    mismatched += 1
                    all_mismatches.append(subject + " Q" + qn + ": DB=" + repr(db_ans) + " PDF=" + repr(pdf_ans))
            
            total_matched += matched
            total_mismatched += mismatched
            total_unverifiable += unverifiable
            print(subject + ": matched=" + str(matched) + " mismatched=" + str(mismatched) + " unverifiable=" + str(unverifiable))
        
        print("\n=== Total ===")
        print("matched: " + str(total_matched))
        print("mismatched: " + str(total_mismatched))
        print("unverifiable: " + str(total_unverifiable))
        
        if all_mismatches:
            print("\nAll mismatches:")
            for m in all_mismatches:
                print("  " + m)
        else:
            print("\n*** NO MISMATCHES ***")

    finally:
        await conn.close()

asyncio.run(main())

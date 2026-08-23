#!/usr/bin/env python3
"""对抗性审查：验证管线 answer_matcher 的答案是否与 PDF 答案表一致。

对每个学科，抽取 3 道题，人工核对：
1. DB 答案 vs PDF 答案表中的答案
2. 检查答案来源（provenance）
"""
import asyncio
import json
import re
import sys
import io

if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"

def compact_text(text):
    if not text:
        return ""
    out = []
    for ch in str(text):
        code = ord(ch)
        if ch in "\u2018\u2019":
            out.append("'")
            continue
        if ch in "\u201c\u201d":
            out.append('"')
            continue
        if ch == "\u3000":
            continue
        if 0xFF01 <= code <= 0xFF5E:
            out.append(chr(code - 0xFEE0))
            continue
        if ch.isspace():
            continue
        out.append(ch)
    return "".join(out)

def extract_answer_table(text):
    """Parse HTML answer table to get {question_number: answer} mapping."""
    table = {}
    # Find HTML table
    table_match = re.search(r"<table>.*?</table>", text, re.DOTALL)
    if not table_match:
        return table
    
    qnums = []
    answers = []
    for row in re.findall(r"<tr>(.*?)</tr>", table_match.group(0), re.DOTALL):
        tds = [t.strip() for t in re.findall(r"<td>(.*?)</td>", row)]
        if not tds:
            continue
        if tds[0] == "题号":
            qnums = [t for t in tds[1:] if t.isdigit()]
        elif tds[0] == "答案" and qnums:
            answers = tds[1:]
    
    if qnums and answers:
        for qn, ans in zip(qnums, answers):
            table[qn] = ans.strip()
    
    return table

def extract_answer_section(text):
    if not text:
        return ""
    patterns = ["参考答案", "答案[：:]", r"Answer\s*Key", "【答案】"]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return text[m.start():]
    return ""

def find_inline_answers(text):
    """Parse inline answer format: 【答案】content or 1.C2.B..."""
    answers = {}
    # Pattern: 【答案】 followed by content
    for m in re.finditer(r"【答案】\s*(.*?)(?=【|$)", text, re.DOTALL):
        content = m.group(1).strip()
        # Extract question numbers and answers
        for qm in re.finditer(r"(\d+)\s*[.．]\s*([A-D]{1,4})", content):
            answers[qm.group(1)] = qm.group(2)
    # Pattern: 1.C2.B3.A... (inline without 【答案】)
    for m in re.finditer(r"(\d+)\s*[.．]\s*([A-D]{1,4})", text):
        qn = m.group(1)
        if qn not in answers:
            answers[qn] = m.group(2)
    return answers

async def main():
    import asyncpg
    conn = await asyncpg.connect(DSN)
    try:
        rows = await conn.fetch(
            "SELECT id, filename, subject, native_markdown, ocr_markdown "
            "FROM documents WHERE processing_status='completed' ORDER BY subject"
        )

        for row in rows:
            subject = row["subject"]
            source = row["ocr_markdown"] or row["native_markdown"] or ""
            
            # Extract answer table from source
            table_answers = extract_answer_table(source)
            
            # Extract inline answers
            answer_section = extract_answer_section(source)
            inline_answers = find_inline_answers(answer_section)
            
            # Get DB answers
            db_rows = await conn.fetch(
                """
                SELECT qi.source_question_number, q.answer, q.sub_questions
                FROM questions q
                JOIN question_instances qi ON qi.question_id = q.id
                WHERE qi.document_id = $1
                ORDER BY qi.source_question_number::int
                """,
                str(row["id"]),
            )

            print(f"\n=== {subject} ===")
            print(f"  Table answers: {len(table_answers)}")
            print(f"  Inline answers: {len(inline_answers)}")
            
            # Check first 3 questions
            mismatches = []
            for r in db_rows[:5]:
                qn = r["source_question_number"]
                db_answer = (r["answer"] or "").strip()
                
                # Get expected answer from table or inline
                expected = table_answers.get(qn) or inline_answers.get(qn)
                
                if expected:
                    # Compare
                    db_norm = compact_text(db_answer).upper().replace(" ", "")
                    exp_norm = compact_text(expected).upper().replace(" ", "")
                    
                    if db_norm == exp_norm:
                        print(f"  Q{qn}: DB='{db_answer}' PDF='{expected}' ✓ MATCH")
                    else:
                        print(f"  Q{qn}: DB='{db_answer}' PDF='{expected}' ✗ MISMATCH")
                        mismatches.append((qn, db_answer, expected))
                else:
                    print(f"  Q{qn}: DB='{db_answer}' PDF=N/A (no table answer)")

            if mismatches:
                print(f"  *** {len(mismatches)} MISMATCHES ***")
            else:
                print(f"  All checked questions match PDF answer table")

    finally:
        await conn.close()

asyncio.run(main())

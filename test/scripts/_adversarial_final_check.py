#!/usr/bin/env python3
"""对抗性审查：正确解析 HTML 表格，验证管线答案与 PDF 答案表的一致性。"""
import asyncio
import json
import re
import sys
import io

if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"

def extract_answer_table(text):
    """Parse HTML answer table - handle multiple row pairs."""
    table = {}
    # Find all HTML tables
    for table_match in re.finditer(r"<table>.*?</table>", text, re.DOTALL):
        table_text = table_match.group(0)
        rows = re.findall(r"<tr>(.*?)</tr>", table_text, re.DOTALL)
        
        # Process pairs of rows (题号 + 答案)
        i = 0
        while i < len(rows) - 1:
            tds_num = [t.strip() for t in re.findall(r"<td>(.*?)</td>", rows[i])]
            tds_ans = [t.strip() for t in re.findall(r"<td>(.*?)</td>", rows[i+1])]
            
            if tds_num and tds_num[0] == "题号" and tds_ans and tds_ans[0] == "答案":
                qnums = [t for t in tds_num[1:] if t.isdigit()]
                answers = tds_ans[1:]
                for qn, ans in zip(qnums, answers):
                    table[qn] = ans.strip()
                i += 2
            else:
                i += 1
    
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
    """Parse inline answer format."""
    answers = {}
    # Pattern: 【答案】 followed by content
    for m in re.finditer(r"【答案】\s*(.*?)(?=【|$)", text, re.DOTALL):
        content = m.group(1).strip()
        for qm in re.finditer(r"(\d+)\s*[.．]\s*([A-D]{1,4})", content):
            answers[qm.group(1)] = qm.group(2)
    # Pattern: 1.C2.B3.A... (inline)
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

        total_verified = 0
        total_mismatch = 0
        all_mismatches = []

        for row in rows:
            subject = row["subject"]
            source = row["ocr_markdown"] or row["native_markdown"] or ""
            
            # Extract answers from PDF
            answer_section = extract_answer_section(source)
            table_answers = extract_answer_table(answer_section)
            inline_answers = find_inline_answers(answer_section)
            
            # Get DB answers
            db_rows = await conn.fetch(
                """
                SELECT qi.source_question_number, q.answer
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
            
            mismatches = []
            verified = 0
            for r in db_rows:
                qn = r["source_question_number"]
                db_answer = (r["answer"] or "").strip()
                
                expected = table_answers.get(qn) or inline_answers.get(qn)
                
                if expected:
                    verified += 1
                    db_norm = db_answer.upper().replace(" ", "")
                    exp_norm = expected.upper().replace(" ", "")
                    
                    if db_norm == exp_norm:
                        pass  # Match
                    else:
                        mismatches.append((qn, db_answer, expected))
            
            print(f"  Verified: {verified}/{len(db_rows)}")
            if mismatches:
                print(f"  *** MISMATCHES: {len(mismatches)} ***")
                for qn, db, pdf in mismatches[:5]:
                    print(f"    Q{qn}: DB='{db}' PDF='{pdf}'")
                total_mismatch += len(mismatches)
            else:
                print(f"  All verified questions match ✓")
            
            total_verified += verified
            all_mismatches.extend([(subject, qn, db, pdf) for qn, db, pdf in mismatches])

        print(f"\n{'='*60}")
        print(f"TOTAL: {total_verified} verified, {total_mismatch} mismatches")
        if all_mismatches:
            print(f"\nAll mismatches:")
            for subject, qn, db, pdf in all_mismatches:
                print(f"  {subject} Q{qn}: DB='{db}' PDF='{pdf}'")

    finally:
        await conn.close()

asyncio.run(main())

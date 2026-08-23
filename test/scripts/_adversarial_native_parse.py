#!/usr/bin/env python3
"""对抗性审查：正确解析 native_markdown 的纯文本答案表，验证管线答案。"""
import asyncio
import re
import sys
import io

if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"

def extract_answer_section(text):
    if not text:
        return ""
    patterns = ["参考答案", "答案[：:]", r"Answer\s*Key", "【答案】"]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return text[m.start():]
    return ""

def parse_native_table(text):
    """Parse native_markdown text table format:
    题号  1  2  3  4  5  6  7  8  9  10
    答案  B  D  D  C  A  D  D  C  C  B
    """
    answers = {}
    lines = text.split('\n')
    
    i = 0
    while i < len(lines) - 1:
        line = lines[i].strip()
        next_line = lines[i + 1].strip()
        
        # Check if this is a "题号" line followed by "答案" line
        if line.startswith('题号') and next_line.startswith('答案'):
            # Parse question numbers
            qnums_part = line[2:].strip()  # Remove "题号"
            qnums = qnums_part.split()
            
            # Parse answers
            answers_part = next_line[2:].strip()  # Remove "答案"
            ans_list = answers_part.split()
            
            # Map question numbers to answers
            for qn, ans in zip(qnums, ans_list):
                if qn.isdigit():
                    answers[qn] = ans.strip()
            
            i += 2
        else:
            i += 1
    
    return answers

def parse_inline_answers(text):
    """Parse inline answer format: 【答案】content or 1.C2.B..."""
    answers = {}
    for m in re.finditer(r"【答案】\s*(.*?)(?=【|$)", text, re.DOTALL):
        content = m.group(1).strip()
        for qm in re.finditer(r"(\d+)\s*[.．]\s*([A-D]{1,4})", content):
            answers[qm.group(1)] = qm.group(2)
    for m in re.finditer(r"(\d+)\s*[.．]\s*([A-D]{1,4})", text):
        qn = m.group(1)
        if qn not in answers:
            answers[qn] = m.group(2)
    return answers

def parse_html_table(text):
    """Parse HTML answer table."""
    answers = {}
    for table_match in re.finditer(r"<table>.*?</table>", text, re.DOTALL):
        table_text = table_match.group(0)
        rows = re.findall(r"<tr>(.*?)</tr>", table_text, re.DOTALL)
        
        i = 0
        while i < len(rows) - 1:
            tds_num = [t.strip() for t in re.findall(r"<td>(.*?)</td>", rows[i])]
            tds_ans = [t.strip() for t in re.findall(r"<td>(.*?)</td>", rows[i+1])]
            
            if tds_num and tds_num[0] == "题号" and tds_ans and tds_ans[0] == "答案":
                qnums = [t for t in tds_num[1:] if t.isdigit()]
                ans_list = tds_ans[1:]
                for qn, ans in zip(qnums, ans_list):
                    answers[qn] = ans.strip()
                i += 2
            else:
                i += 1
    
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
            native = row["native_markdown"] or ""
            ocr = row["ocr_markdown"] or ""
            
            # Extract answer sections
            native_answer_section = extract_answer_section(native)
            ocr_answer_section = extract_answer_section(ocr)
            
            # Parse answers from native (primary) and ocr (secondary)
            native_table = parse_native_table(native_answer_section)
            native_inline = parse_inline_answers(native_answer_section)
            ocr_table = parse_html_table(ocr_answer_section)
            ocr_inline = parse_inline_answers(ocr_answer_section)
            
            # Merge: native takes priority
            native_answers = {**native_table, **native_inline}
            ocr_answers = {**ocr_table, **ocr_inline}
            
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
            print(f"  Native answers: {len(native_answers)}")
            print(f"  OCR answers: {len(ocr_answers)}")
            
            mismatches = []
            verified = 0
            unverifiable = 0
            
            for r in db_rows:
                qn = r["source_question_number"]
                db_answer = (r["answer"] or "").strip()
                
                # Get expected answer: native first, then ocr
                expected = native_answers.get(qn) or ocr_answers.get(qn)
                source = "native" if qn in native_answers else ("ocr" if qn in ocr_answers else None)
                
                if expected:
                    verified += 1
                    db_norm = db_answer.upper().replace(" ", "")
                    exp_norm = expected.upper().replace(" ", "")
                    
                    if db_norm == exp_norm:
                        pass  # Match
                    else:
                        mismatches.append((qn, db_answer, expected, source))
                else:
                    unverifiable += 1
            
            print(f"  Verified: {verified}/{len(db_rows)}")
            print(f"  Unverifiable: {unverifiable}/{len(db_rows)}")
            
            if mismatches:
                print(f"  *** MISMATCHES: {len(mismatches)} ***")
                for qn, db, expected, source in mismatches:
                    print(f"    Q{qn}: DB='{db}' {source}='{expected}'")
                total_mismatch += len(mismatches)
            else:
                print(f"  All verified questions match ✓")
            
            total_verified += verified
            all_mismatches.extend([(subject, qn, db, exp, src) for qn, db, exp, src in mismatches])

        print(f"\n{'='*60}")
        print(f"TOTAL: {total_verified} verified, {total_mismatch} mismatches")
        if all_mismatches:
            print(f"\nAll mismatches:")
            for subject, qn, db, expected, source in all_mismatches:
                print(f"  {subject} Q{qn}: DB='{db}' {source}='{expected}'")

    finally:
        await conn.close()

asyncio.run(main())

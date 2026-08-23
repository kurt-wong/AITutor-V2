#!/usr/bin/env python3
"""对抗性审查：检查各学科 native_markdown vs ocr_markdown 的答案区差异。"""
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

def parse_html_table(text):
    """Parse HTML answer table to get {question_number: answer} mapping."""
    table = {}
    for table_match in re.finditer(r"<table>.*?</table>", text, re.DOTALL):
        table_text = table_match.group(0)
        rows = re.findall(r"<tr>(.*?)</tr>", table_text, re.DOTALL)
        
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
            native = row["native_markdown"] or ""
            ocr = row["ocr_markdown"] or ""
            
            print(f"\n=== {subject} ===")
            print(f"  native_markdown: {len(native)} chars")
            print(f"  ocr_markdown: {len(ocr)} chars")
            
            # Extract answer sections
            native_answer_section = extract_answer_section(native)
            ocr_answer_section = extract_answer_section(ocr)
            
            print(f"  native answer section: {len(native_answer_section)} chars")
            print(f"  ocr answer section: {len(ocr_answer_section)} chars")
            
            # Parse answers from both sources
            native_table = parse_html_table(native_answer_section)
            ocr_table = parse_html_table(ocr_answer_section)
            native_inline = parse_inline_answers(native_answer_section)
            ocr_inline = parse_inline_answers(ocr_answer_section)
            
            print(f"  native table answers: {len(native_table)}")
            print(f"  ocr table answers: {len(ocr_table)}")
            print(f"  native inline answers: {len(native_inline)}")
            print(f"  ocr inline answers: {len(ocr_inline)}")
            
            # Compare native vs ocr
            all_qns = set(native_table.keys()) | set(ocr_table.keys()) | set(native_inline.keys()) | set(ocr_inline.keys())
            
            mismatches = []
            for qn in sorted(all_qns, key=lambda x: int(x) if x.isdigit() else 0):
                native_ans = native_table.get(qn) or native_inline.get(qn)
                ocr_ans = ocr_table.get(qn) or ocr_inline.get(qn)
                
                if native_ans and ocr_ans:
                    if native_ans != ocr_ans:
                        mismatches.append((qn, native_ans, ocr_ans))
                elif native_ans and not ocr_ans:
                    pass  # native has it, ocr doesn't
                elif not native_ans and ocr_ans:
                    pass  # ocr has it, native doesn't
            
            if mismatches:
                print(f"  *** native vs ocr MISMATCHES: {len(mismatches)} ***")
                for qn, native, ocr in mismatches[:5]:
                    print(f"    Q{qn}: native='{native}' ocr='{ocr}'")
            else:
                print(f"  native vs ocr: all match ✓")

    finally:
        await conn.close()

asyncio.run(main())

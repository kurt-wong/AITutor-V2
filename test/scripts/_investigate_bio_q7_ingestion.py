#!/usr/bin/env python3
"""调查生物 Q7 答案从 A 变 D 的入库过程。"""
import sys
import io
import asyncio
import json
if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

async def main():
    import asyncpg
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:15432/aitutors")
    try:
        doc = await conn.fetchrow("""
            SELECT id, filename, llm_annotated_markdown, ocr_markdown, native_markdown
            FROM documents
            WHERE subject = '生物' AND processing_status = 'completed'
            ORDER BY created_at DESC LIMIT 1
        """)
        if not doc:
            print("No biology doc found")
            return

        doc_id = str(doc["id"])
        print(f"Doc: {doc['filename']}")

        # Check OCR markdown for Q7 answer
        ocr = doc["ocr_markdown"] or ""
        import re
        
        # Find Q7 in OCR answer section
        answer_section_match = re.search("参考答案", ocr)
        if answer_section_match:
            answer_section = ocr[answer_section_match.start():]
            # Look for Q7 in the answer table
            lines = answer_section.split("\n")
            for i, line in enumerate(lines[:30]):
                if "7" in line and ("答案" in line or "D" in line or "A" in line):
                    print(f"  OCR L{i}: {repr(line[:80])}")

        # Check L2 annotation for Q7 answer_line_ids
        l2_raw = doc["llm_annotated_markdown"] or "{}"
        try:
            l2_data = json.loads(l2_raw)
        except:
            l2_data = {}
        
        questions = l2_data.get("questions", [])
        for q in questions:
            qno = str(q.get("question_number", ""))
            if qno == "7":
                print(f"\nL2 Q7:")
                print(f"  answer: {repr(q.get('answer'))}")
                print(f"  answer_line_ids: {q.get('answer_line_ids')}")
                # Check what P9L003 contains
                print(f"  P9L003 is the answer_line_id - need to check what this line contains")

        # Check task result for answer matching details
        task = await conn.fetchrow("""
            SELECT result_json
            FROM background_tasks
            WHERE payload_json->>'document_id' = $1
            ORDER BY created_at DESC LIMIT 1
        """, doc_id)
        if task:
            result = task["result_json"]
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except:
                    result = {}
            
            # Check for answer matching details
            questions_result = result.get("questions", [])
            for q in questions_result:
                if isinstance(q, dict):
                    qno = str(q.get("question_number", ""))
                    if qno == "7":
                        print(f"\nPipeline Q7:")
                        print(f"  answer: {repr(q.get('answer'))}")
                        print(f"  answer_provenance: {q.get('answer_provenance')}")
                        print(f"  answer_line_ids: {q.get('answer_line_ids')}")
                        print(f"  All keys: {list(q.keys())}")

        # Check if there's an answer table in the OCR that might have Q7=D
        # Parse the OCR answer table
        ocr_answer_section = ""
        if answer_section_match:
            ocr_answer_section = ocr[answer_section_match.start():]
        
        # Look for HTML table
        table_match = re.search(r"<table>.*?</table>", ocr_answer_section, re.DOTALL)
        if table_match:
            table_text = table_match.group(0)
            rows = re.findall(r"<tr>(.*?)</tr>", table_text, re.DOTALL)
            print(f"\nOCR HTML table ({len(rows)} rows):")
            for i, row in enumerate(rows[:4]):
                tds = re.findall(r"<td>(.*?)</td>", row)
                print(f"  Row {i}: {tds[:12]}")

    finally:
        await conn.close()

asyncio.run(main())

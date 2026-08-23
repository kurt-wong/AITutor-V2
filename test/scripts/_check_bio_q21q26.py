#!/usr/bin/env python3
"""检查生物 Q21-Q26 综合题的 DB 答案 vs PDF 答案。"""
import sys, io, asyncio, json, re
if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

async def main():
    import asyncpg
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:15432/aitutors")
    try:
        doc = await conn.fetchrow("""
            SELECT id, filename FROM documents
            WHERE subject = '生物' ORDER BY created_at DESC LIMIT 1
        """)
        if not doc:
            print("No biology doc")
            return
        doc_id = str(doc["id"])

        # Q21-Q26 from DB
        print("=== DB answers for Q21-Q26 ===")
        for qn in ["21", "22", "23", "24", "25", "26"]:
            row = await conn.fetchrow("""
                SELECT q.answer, q.sub_questions, q.is_composite
                FROM questions q
                JOIN question_instances qi ON qi.question_id = q.id
                WHERE qi.document_id = $1 AND qi.source_question_number = $2
            """, doc_id, qn)
            if row:
                subs = row["sub_questions"]
                if isinstance(subs, str):
                    try: subs = json.loads(subs)
                    except: subs = []
                print("Q" + qn + ": answer=" + repr((row["answer"] or "")[:60]) + " composite=" + str(row["is_composite"]))
                if subs:
                    for s in subs[:3]:
                        if isinstance(s, dict):
                            print("   sub qno=" + str(s.get("qno")) + " ans=" + repr((s.get("answer") or "")[:40]))

        # PDF answers for Q21-Q26
        import fitz
        pdf_path = r"test/pdf/2026北京北师大附中高一（上）期末生物（教师版）.pdf"
        pdf_doc = fitz.open(pdf_path)
        pdf_text = ""
        for page in pdf_doc:
            pdf_text += page.get_text("text")
        pdf_doc.close()

        idx = pdf_text.find("参考答案")
        section = pdf_text[idx:]
        print("\n=== PDF answer section (Q21+) ===")
        q21_pos = section.find("21.")
        if q21_pos >= 0:
            print(section[q21_pos:q21_pos+600])
        else:
            print("Q21 not found in answer section")

    finally:
        await conn.close()

asyncio.run(main())

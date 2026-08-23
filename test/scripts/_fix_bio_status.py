#!/usr/bin/env python3
import asyncio, asyncpg, sys, io
if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

async def main():
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:15432/aitutors")
    try:
        # Update document status
        await conn.execute("""
            UPDATE documents SET processing_status = 'completed'
            WHERE id = 'd67ce95f-b15e-426c-95e5-a5fd07a61573'
        """)
        print("Document status updated to completed")

        # Verify Q6 and Q7
        import fitz
        pdf_path = r"test/pdf/2026北京北师大附中高一（上）期末生物（教师版）.pdf"
        doc_pdf = fitz.open(pdf_path)
        pdf_text = ""
        for page in doc_pdf:
            pdf_text += page.get_text("text")
        doc_pdf.close()

        idx = pdf_text.find("参考答案")
        section = pdf_text[idx:]
        lines = section.split("\n")
        
        qnums = []
        answers = []
        for line in lines[:30]:
            line = line.strip()
            if line == "题号":
                qnums = []
            elif line == "答案":
                answers = []
            elif line.isdigit() and not answers:
                qnums.append(line)
            elif line and not line.isdigit() and qnums and len(answers) < len(qnums):
                answers.append(line)

        pdf_answers = dict(zip(qnums, answers))

        doc_id = "d67ce95f-b15e-426c-95e5-a5fd07a61573"
        print("\n=== Q6/Q7 Verification ===")
        for qn in ["6", "7"]:
            row = await conn.fetchrow("""
                SELECT q.answer FROM questions q
                JOIN question_instances qi ON qi.question_id = q.id
                WHERE qi.document_id = $1 AND qi.source_question_number = $2
            """, doc_id, qn)
            db_answer = row["answer"] if row else None
            pdf_answer = pdf_answers.get(qn)
            match = db_answer == pdf_answer
            print("Q" + qn + ": DB=" + repr(db_answer) + " PDF=" + repr(pdf_answer) + " " + ("MATCH" if match else "MISMATCH"))

    finally:
        await conn.close()

asyncio.run(main())

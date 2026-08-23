#!/usr/bin/env python3
"""调查生物 Q6/Q7 答案错误来源。"""
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
        # Get biology document
        doc = await conn.fetchrow("""
            SELECT id, filename, llm_annotated_markdown
            FROM documents
            WHERE subject = '生物' AND processing_status = 'completed'
            ORDER BY created_at DESC LIMIT 1
        """)
        if not doc:
            print("No biology doc found")
            return

        doc_id = str(doc["id"])
        print(f"Doc: {doc['filename']}")

        # Get Q6 and Q7 from DB
        for qn in ["6", "7"]:
            row = await conn.fetchrow("""
                SELECT q.id, q.stem, q.answer, q.sub_questions, q.status, q.review_reason,
                       qi.source_question_number
                FROM questions q
                JOIN question_instances qi ON qi.question_id = q.id
                WHERE qi.document_id = $1 AND qi.source_question_number = $2
            """, doc_id, qn)
            if row:
                print(f"\nQ{qn}:")
                print(f"  DB answer: {repr(row['answer'])}")
                print(f"  status: {row['status']}")
                print(f"  review_reason: {row['review_reason']}")
                print(f"  stem (first 100): {repr(row['stem'][:100] if row['stem'] else None)}")

        # Check L2 annotation for Q6 and Q7
        l2_raw = doc["llm_annotated_markdown"] or "{}"
        try:
            l2_data = json.loads(l2_raw)
        except:
            l2_data = {}
        
        questions = l2_data.get("questions", [])
        for q in questions:
            qno = str(q.get("question_number", ""))
            if qno in ["6", "7"]:
                print(f"\nL2 Q{qno}:")
                print(f"  answer: {repr(q.get('answer'))}")
                print(f"  answer_line_ids: {q.get('answer_line_ids')}")
                print(f"  sub_questions: {q.get('sub_questions')}")

        # Check task result for answer extraction details
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
            # Check for answer extraction details
            questions_result = result.get("questions", [])
            for q in questions_result:
                if isinstance(q, dict):
                    qno = str(q.get("question_number", ""))
                    if qno in ["6", "7"]:
                        print(f"\nPipeline Q{qno}:")
                        print(f"  answer: {repr(q.get('answer'))}")
                        print(f"  answer_provenance: {q.get('answer_provenance')}")

    finally:
        await conn.close()

asyncio.run(main())

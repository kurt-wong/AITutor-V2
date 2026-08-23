#!/usr/bin/env python3
"""诊断 DB 中实际存储的答案：检查管线 answer_matcher 是否正确提取了答案。"""
import asyncio
import json
import sys
import io

if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"

async def main():
    import asyncpg
    conn = await asyncpg.connect(DSN)
    try:
        rows = await conn.fetch(
            "SELECT DISTINCT subject FROM documents WHERE processing_status='completed' ORDER BY subject"
        )
        subjects = [r["subject"] for r in rows]

        for subject in subjects:
            doc = await conn.fetchrow(
                "SELECT id, filename FROM documents "
                "WHERE subject=$1 AND processing_status='completed' "
                "ORDER BY created_at DESC LIMIT 1",
                subject,
            )
            if not doc:
                continue

            db_rows = await conn.fetch(
                """
                SELECT qi.source_question_number, q.stem, q.answer, q.options,
                       q.is_composite, q.sub_questions, q.status
                FROM questions q
                JOIN question_instances qi ON qi.question_id = q.id
                WHERE qi.document_id = $1
                ORDER BY qi.source_question_number::int
                """,
                str(doc["id"]),
            )

            has_answer = 0
            no_answer = 0
            examples = []
            for r in db_rows:
                qn = r["source_question_number"]
                answer = r["answer"]
                subs = r["sub_questions"]
                if isinstance(subs, str):
                    try:
                        subs = json.loads(subs)
                    except:
                        subs = []

                if answer:
                    has_answer += 1
                elif subs:
                    # Check sub_questions for answers
                    sub_answers = [s.get("answer") for s in (subs or []) if isinstance(s, dict) and s.get("answer")]
                    if sub_answers:
                        has_answer += 1
                    else:
                        no_answer += 1
                        examples.append(qn)
                else:
                    no_answer += 1
                    examples.append(qn)

            total = has_answer + no_answer
            print(f"{subject}: {has_answer}/{total} have answer, {no_answer} missing")
            if examples:
                print(f"  Missing: {examples[:10]}")

    finally:
        await conn.close()

asyncio.run(main())

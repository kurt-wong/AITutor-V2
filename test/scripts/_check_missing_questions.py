#!/usr/bin/env python3
"""独立复核：检查 missing_db_question 的具体情况。"""
import sys
import io
import asyncio
if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

async def main():
    import asyncpg
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:15432/aitutors")
    try:
        missing_questions = [
            ("历史", "37"),
            ("地理", "21"), ("地理", "23"), ("地理", "24"), ("地理", "25"), ("地理", "30"),
            ("物理", "20"),
            ("生物", "1"), ("生物", "2"),
            ("英语", "46"),
            ("语文", "24"),
        ]
        
        for subject, qn in missing_questions:
            row = await conn.fetchrow("""
                SELECT q.id, q.stem, q.answer
                FROM questions q
                JOIN question_instances qi ON qi.question_id = q.id
                JOIN documents d ON qi.document_id = d.id
                WHERE d.subject = $1 AND qi.source_question_number = $2
                AND d.processing_status = 'completed'
                ORDER BY d.created_at DESC LIMIT 1
            """, subject, qn)
            if row:
                stem = row["stem"] or ""
                answer = row["answer"] or ""
                print(f"{subject} Q{qn}: stem_len={len(stem)}, answer={repr(answer[:30])}")
            else:
                print(f"{subject} Q{qn}: NOT IN DB (missing_db_question)")
    finally:
        await conn.close()

asyncio.run(main())

"""检查当前 DB 状态：文档、题目、学科分布。"""
import asyncio
import asyncpg
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"

async def main():
    conn = await asyncpg.connect(DSN)
    try:
        # 当前文档状态
        rows = await conn.fetch("""
            SELECT processing_status, COUNT(*) AS cnt
            FROM documents GROUP BY processing_status ORDER BY processing_status
        """)
        print("=== 文档状态 ===")
        for r in rows:
            print(f"  {r['processing_status']}: {r['cnt']}")

        # 当前题目数
        qcnt = await conn.fetchval("SELECT COUNT(*) FROM questions")
        icnt = await conn.fetchval("SELECT COUNT(*) FROM question_instances")
        print(f"\n=== 题目 ===")
        print(f"  questions: {qcnt}")
        print(f"  question_instances: {icnt}")

        # 按学科统计
        rows = await conn.fetch("""
            SELECT d.subject, COUNT(DISTINCT d.id) AS docs, COUNT(qi.id) AS questions
            FROM documents d
            LEFT JOIN question_instances qi ON qi.document_id = d.id
            WHERE d.processing_status = 'completed'
            GROUP BY d.subject ORDER BY d.subject
        """)
        print(f"\n=== 按学科(completed) ===")
        for r in rows:
            print(f"  {r['subject']}: {r['docs']} docs, {r['questions']} questions")

        # 列出所有文档
        rows = await conn.fetch("""
            SELECT id, filename, subject, processing_status,
                   (SELECT COUNT(*) FROM question_instances qi WHERE qi.document_id = d.id) AS q_count
            FROM documents d ORDER BY d.subject, d.filename
        """)
        print(f"\n=== 全部文档({len(rows)}) ===")
        for r in rows:
            subj = r['subject'] or '?'
            status = r['processing_status']
            qc = r['q_count']
            fn = r['filename'][:60]
            print(f"  {subj:6s} | {status:10s} | {qc:3d}q | {fn}")
    finally:
        await conn.close()

asyncio.run(main())

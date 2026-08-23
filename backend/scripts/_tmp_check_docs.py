"""检查当前DB中已有的文档和可用PDF。"""
import asyncio, asyncpg, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"

async def main():
    conn = await asyncpg.connect(DSN)
    try:
        rows = await conn.fetch("""
            SELECT id, subject, processing_status,
                   (SELECT COUNT(*) FROM question_instances qi WHERE qi.document_id = d.id) AS q_count,
                   filename
            FROM documents d ORDER BY d.subject, d.filename
        """)
        print(f"=== 当前文档 ({len(rows)}) ===")
        for r in rows:
            subj = r['subject'] or '?'
            status = r['processing_status']
            qc = r['q_count']
            print(f"  {subj:4s} | {status:10s} | {qc:3d}q | {r['filename'][:50]}")

        qcnt = await conn.fetchval("SELECT COUNT(*) FROM questions")
        print(f"\nquestions: {qcnt}")
    finally:
        await conn.close()

asyncio.run(main())

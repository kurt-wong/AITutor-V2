"""检查文档和任务状态。"""
import asyncio, asyncpg, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"

async def main():
    conn = await asyncpg.connect(DSN)
    try:
        # 文档状态
        rows = await conn.fetch("""
            SELECT d.id, d.filename, d.processing_status, d.subject,
                   d.error_message
            FROM documents d ORDER BY d.created_at
        """)
        print("=== 文档状态 ===")
        for r in rows:
            subj = r['subject'] or '?'
            fn = r['filename'] or '?'
            status = r['processing_status']
            err = (r['error_message'] or '')[:80]
            print(f"  {subj:4s} | {status:10s} | err={err} | {fn[:50]}")

        # 任务状态
        rows = await conn.fetch("""
            SELECT bt.id, bt.status, bt.task_type, bt.result_json,
                   bt.metadata_json::text as meta
            FROM background_tasks bt ORDER BY bt.created_at
        """)
        print(f"\n=== 任务状态（{len(rows)}） ===")
        for r in rows:
            status = r['status']
            ttype = r['task_type'] or '?'
            result = (r['result_json'] or '')[:120]
            meta = (r['meta'] or '')[:80]
            print(f"  {ttype:15s} | {status:10s} | result={result}")

        # 检查是否有题目
        qcnt = await conn.fetchval("SELECT COUNT(*) FROM questions")
        icnt = await conn.fetchval("SELECT COUNT(*) FROM question_instances")
        print(f"\n=== 题目 ===")
        print(f"  questions: {qcnt}")
        print(f"  question_instances: {icnt}")

        # 检查 processing_logs
        rows = await conn.fetch("""
            SELECT dpl.stage, dpl.message, dpl.created_at
            FROM document_processing_logs dpl
            ORDER BY dpl.created_at DESC LIMIT 20
        """)
        print(f"\n=== 最近处理日志（{len(rows)}） ===")
        for r in rows:
            stage = r['stage'] or '?'
            msg = (r['message'] or '')[:100]
            print(f"  {stage:20s} | {msg}")
    finally:
        await conn.close()

asyncio.run(main())

import asyncio, asyncpg, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"
async def main():
    conn = await asyncpg.connect(DSN)
    try:
        # 查看还在 processing 的文档
        rows = await conn.fetch("""
            SELECT d.id, d.filename, d.subject, d.processing_status
            FROM documents d WHERE d.processing_status != 'completed'
        """)
        print("=== 未完成文档 ===")
        for r in rows:
            print(f"  {r['subject']} | {r['processing_status']} | {r['filename'][:60]}")
            doc_id = r['id']
            # 查看该文档的处理日志
            logs = await conn.fetch("""
                SELECT stage, message, created_at
                FROM document_processing_logs
                WHERE document_id = $1
                ORDER BY created_at DESC LIMIT 10
            """, doc_id)
            print(f"  最近日志:")
            for l in logs:
                print(f"    {l['created_at']} | {l['stage']} | {(l['message'] or '')[:80]}")

        # 查看 running 任务的 current_stage
        tasks = await conn.fetch("""
            SELECT id, status, current_stage, progress, error_detail
            FROM background_tasks WHERE status = 'running'
        """)
        print(f"\n=== 运行中的任务 ===")
        for t in tasks:
            print(f"  task={t['id']} | stage={t['current_stage']} | progress={t['progress']} | err={t['error_detail'] or ''}")

        # 最近的 questions (看是否有新入库)
        qcnt = await conn.fetchval("SELECT COUNT(*) FROM questions")
        icnt = await conn.fetchval("SELECT COUNT(*) FROM question_instances")
        print(f"\nquestions={qcnt} instances={icnt}")
    finally:
        await conn.close()
asyncio.run(main())

"""轮询监控5科管线执行，直到全部完成。"""
import asyncio, asyncpg, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"

async def main():
    conn = await asyncpg.connect(DSN)
    start = time.time()
    
    try:
        while time.time() - start < 3600:  # 1小时超时
            # 任务状态
            tasks = await conn.fetch("""
                SELECT status, COUNT(*) AS cnt
                FROM background_tasks GROUP BY status ORDER BY status
            """)
            task_map = {r['status']: r['cnt'] for r in tasks}
            
            # 文档状态
            docs = await conn.fetch("""
                SELECT subject, processing_status,
                       (SELECT COUNT(*) FROM question_instances qi WHERE qi.document_id = d.id) AS q_count
                FROM documents d ORDER BY d.subject
            """)
            
            completed = sum(1 for d in docs if d['processing_status'] == 'completed')
            total = len(docs)
            
            elapsed = time.time() - start
            print(f"\n[{elapsed/60:.0f}min] === 管线进度 ===")
            print(f"  任务: {dict(task_map)}")
            print(f"  文档: {completed}/{total} completed")
            for d in docs:
                icon = "✅" if d['processing_status'] == 'completed' else "⏳"
                print(f"    {icon} {d['subject']}: {d['processing_status']} ({d['q_count']}题)")
            
            # 全部完成？
            if completed >= total:
                total_q = await conn.fetchval("SELECT COUNT(*) FROM questions")
                print(f"\n=== 全部完成 ===")
                print(f"  总题目数: {total_q}")
                break
            
            await asyncio.sleep(60)
        else:
            print(f"\n[TIMEOUT] 超过 1 小时")
    finally:
        await conn.close()

asyncio.run(main())

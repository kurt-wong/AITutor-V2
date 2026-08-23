"""轮询监控 e2e 全量管线执行。每60秒检查一次，直到全部完成或超时。"""
import asyncio, asyncpg, sys, io, time, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"
POLL_INTERVAL = 60  # 秒
MAX_WAIT = 3600  # 1小时超时

async def main():
    conn = await asyncpg.connect(DSN)
    start = time.time()

    try:
        while time.time() - start < MAX_WAIT:
            # 文档状态
            rows = await conn.fetch("""
                SELECT processing_status, COUNT(*) AS cnt
                FROM documents GROUP BY processing_status ORDER BY processing_status
            """)
            status_map = {r['processing_status']: r['cnt'] for r in rows}
            completed = status_map.get('completed', 0)
            processing = status_map.get('processing', 0)
            pending = status_map.get('pending', 0)
            failed = status_map.get('failed', 0)

            # 任务状态
            tasks = await conn.fetch("""
                SELECT status, COUNT(*) AS cnt
                FROM background_tasks GROUP BY status ORDER BY status
            """)
            task_map = {r['status']: r['cnt'] for r in tasks}

            # 题目数
            qcnt = await conn.fetchval("SELECT COUNT(*) FROM questions")
            icnt = await conn.fetchval("SELECT COUNT(*) FROM question_instances")

            # 按学科统计已完成的题目
            subj_stats = await conn.fetch("""
                SELECT d.subject, COUNT(qi.id) AS questions
                FROM documents d
                LEFT JOIN question_instances qi ON qi.document_id = d.id
                WHERE d.processing_status = 'completed'
                GROUP BY d.subject ORDER BY d.subject
            """)

            elapsed = time.time() - start
            print(f"\n[{elapsed/60:.0f}min] === 管线进度 ===")
            print(f"  文档: completed={completed} processing={processing} pending={pending} failed={failed}")
            print(f"  任务: {dict(task_map)}")
            print(f"  题目: {qcnt} questions, {icnt} instances")

            if subj_stats:
                print(f"  按学科:")
                for r in subj_stats:
                    print(f"    {r['subject']}: {r['questions']}题")

            # 检查失败的任务
            failed_tasks = await conn.fetch("""
                SELECT id, error_detail, result_json::text
                FROM background_tasks WHERE status = 'failed'
                ORDER BY updated_at DESC LIMIT 5
            """)
            if failed_tasks:
                print(f"  失败任务:")
                for ft in failed_tasks:
                    err = (ft['error_detail'] or '')[:100]
                    print(f"    {ft['id']}: {err}")

            # 全部完成？
            if completed >= 10 or (completed + failed >= 10):
                print(f"\n=== 最终结果 ===")
                print(f"  completed={completed} failed={failed}")

                # 详细每份文档
                details = await conn.fetch("""
                    SELECT d.id, d.filename, d.subject, d.processing_status,
                           (SELECT COUNT(*) FROM question_instances qi WHERE qi.document_id = d.id) AS q_count
                    FROM documents d ORDER BY d.subject, d.filename
                """)
                for r in details:
                    subj = r['subject'] or '?'
                    status = r['processing_status']
                    qc = r['q_count']
                    icon = "✅" if status == "completed" else "❌" if status == "failed" else "⏳"
                    print(f"  {icon} {subj:4s} | {status:10s} | {qc:3d}题")

                # 题型/难度分布
                qt_dist = await conn.fetch("""
                    SELECT qt.code, COUNT(*) AS cnt
                    FROM questions q
                    LEFT JOIN question_types qt ON qt.id = q.question_type_id
                    GROUP BY qt.code ORDER BY qt.code
                """)
                print(f"\n  题型分布:")
                for r in qt_dist:
                    print(f"    {r['code']}: {r['cnt']}")

                diff_dist = await conn.fetch("""
                    SELECT difficulty, COUNT(*) AS cnt
                    FROM questions WHERE difficulty IS NOT NULL
                    GROUP BY difficulty ORDER BY difficulty
                """)
                print(f"  难度分布:")
                for r in diff_dist:
                    print(f"    level {r['difficulty']}: {r['cnt']}")

                null_type = await conn.fetchval("SELECT COUNT(*) FROM questions WHERE question_type_id IS NULL")
                null_diff = await conn.fetchval("SELECT COUNT(*) FROM questions WHERE difficulty IS NULL")
                print(f"  NULL题型: {null_type}, NULL难度: {null_diff}")
                break

            await asyncio.sleep(POLL_INTERVAL)

        else:
            print(f"\n[TIMEOUT] 超过 {MAX_WAIT}s，当前状态:")
            completed = status_map.get('completed', 0)
            print(f"  completed={completed} processing={processing} pending={pending}")

    finally:
        await conn.close()

asyncio.run(main())

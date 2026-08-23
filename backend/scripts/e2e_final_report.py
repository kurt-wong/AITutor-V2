"""最终 e2e 验收报告：10份PDF全量管线结果。"""
import asyncio, asyncpg, sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"

async def main():
    conn = await asyncpg.connect(DSN)
    try:
        print("=" * 80)
        print("  e2e 全量验收报告：5科×2份PDF 管线端到端执行")
        print("=" * 80)

        # 每份文档详情
        rows = await conn.fetch("""
            SELECT d.id, d.filename, d.subject, d.processing_status,
                   d.error_message,
                   (SELECT COUNT(*) FROM question_instances qi WHERE qi.document_id = d.id) AS q_count,
                   bt.status as task_status, bt.result_json::text as task_result
            FROM documents d
            LEFT JOIN background_tasks bt ON bt.payload_json->>'document_id' = d.id::text
            ORDER BY d.subject, d.filename
        """)
        print(f"\n{'学科':<6} {'状态':<12} {'题数':>4}  {'任务':<10} 文件名")
        print("-" * 80)
        for r in rows:
            subj = r['subject'] or '?'
            status = r['processing_status']
            qc = r['q_count']
            t_status = r['task_status'] or '?'
            fn = (r['filename'] or '?')[:40]
            icon = "✅" if status == "completed" else "❌"
            print(f"{icon} {subj:<4} {status:<12} {qc:>4}  {t_status:<10} {fn}")

        # 汇总
        completed = sum(1 for r in rows if r['processing_status'] == 'completed')
        failed = sum(1 for r in rows if r['processing_status'] != 'completed')
        total_q = sum(r['q_count'] for r in rows)
        print(f"\n总计: {completed} 成功, {failed} 失败, {total_q} 题")

        # 题型分布
        qt_dist = await conn.fetch("""
            SELECT qt.code, COUNT(*) AS cnt
            FROM questions q
            LEFT JOIN question_types qt ON qt.id = q.question_type_id
            GROUP BY qt.code ORDER BY qt.code
        """)
        print(f"\n题型分布:")
        for r in qt_dist:
            print(f"  {r['code']}: {r['cnt']}")

        # 难度分布
        diff_dist = await conn.fetch("""
            SELECT difficulty, COUNT(*) AS cnt
            FROM questions WHERE difficulty IS NOT NULL
            GROUP BY difficulty ORDER BY difficulty
        """)
        print(f"\n难度分布:")
        for r in diff_dist:
            print(f"  level {r['difficulty']}: {r['cnt']}")

        # NULL 检查
        null_type = await conn.fetchval("SELECT COUNT(*) FROM questions WHERE question_type_id IS NULL")
        null_diff = await conn.fetchval("SELECT COUNT(*) FROM questions WHERE difficulty IS NULL")
        print(f"\nNULL题型: {null_type}, NULL难度: {null_diff}")

        # 按学科统计
        subj_stats = await conn.fetch("""
            SELECT d.subject, COUNT(qi.id) AS questions
            FROM documents d
            LEFT JOIN question_instances qi ON qi.document_id = d.id
            WHERE d.processing_status = 'completed'
            GROUP BY d.subject ORDER BY d.subject
        """)
        print(f"\n按学科统计（completed）:")
        for r in subj_stats:
            print(f"  {r['subject']}: {r['questions']}题")

        # 失败文档详情
        failed_docs = await conn.fetch("""
            SELECT d.id, d.filename, d.subject, d.error_message,
                   bt.status as task_status, bt.error_detail
            FROM documents d
            LEFT JOIN background_tasks bt ON bt.payload_json->>'document_id' = d.id::text
            WHERE d.processing_status != 'completed'
        """)
        if failed_docs:
            print(f"\n失败文档详情:")
            for r in failed_docs:
                fn = (r['filename'] or '?')[:40]
                err = (r['error_detail'] or r['error_message'] or '')[:100]
                print(f"  {r['subject']} | {fn}")
                print(f"    error: {err}")

    finally:
        await conn.close()

asyncio.run(main())

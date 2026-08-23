"""检查物理-八十中任务结果里的重复题号。"""
import asyncio, asyncpg, sys, io, json
from collections import Counter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"

async def main():
    conn = await asyncpg.connect(DSN)
    try:
        # 找物理-八十中相关任务
        rows = await conn.fetch("""
            SELECT bt.id, bt.status, bt.result_json::text as result, bt.payload_json::text as payload,
                   bt.current_stage, bt.progress, bt.error_detail
            FROM background_tasks bt
            WHERE bt.payload_json::text LIKE '%80%E5%85%AB%E5%8D%81%'
               OR bt.payload_json::text LIKE '%4ae383a6%'
            ORDER BY bt.created_at
        """)
        if not rows:
            print("未找到相关任务")
            return

        for r in rows:
            print(f"task={r['id']} | status={r['status']} | stage={r['current_stage']} | progress={r['progress']}")
            print(f"error_detail: {(r['error_detail'] or '')[:200]}")
            result = r['result']
            if not result:
                print("  result_json 为空")
                continue
            try:
                data = json.loads(result)
                # 尝试找 sliced_questions
                sliced = data.get('sliced_questions') or data.get('questions') or []
                print(f"  result keys: {list(data.keys())}")
                print(f"  sliced_questions: {len(sliced)}")
                if sliced:
                    qnos = [str(sq.get('question_number')) for sq in sliced]
                    dup = {k: v for k, v in Counter(qnos).items() if v > 1}
                    print(f"  重复题号: {dup}")
                    for sq in sliced:
                        qn = sq.get('question_number')
                        qt = sq.get('question_type')
                        print(f"    Q{qn} | type={qt}")
            except json.JSONDecodeError:
                print(f"  result 不是 JSON: {result[:200]}")
    finally:
        await conn.close()

asyncio.run(main())

"""查入库后 Q22 的 sub_questions 详情。"""
import asyncio, asyncpg, sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"

async def main():
    conn = await asyncpg.connect(DSN)
    try:
        row = await conn.fetchrow("""
            SELECT q.id, q.stem, q.options, q.answer, q.sub_questions, q.is_composite
            FROM questions q
            JOIN question_instances qi ON qi.question_id = q.id
            JOIN documents d ON d.id = qi.document_id
            WHERE d.subject = '语文' AND qi.source_question_number = '22'
        """)
        if not row:
            print("未找到 Q22")
            return

        print(f"=== 入库 Q22 ===")
        print(f"  stem: {(row['stem'] or '')[:100]}")
        print(f"  options: {row['options']}")
        print(f"  answer: {(row['answer'] or '')[:50]}")
        print(f"  is_composite: {row['is_composite']}")

        subs = row['sub_questions']
        if subs:
            print(f"  sub_questions ({len(subs)}):")
            for i, sub in enumerate(subs[:10]):
                print(f"    [{i}] {sub}")
            if len(subs) > 10:
                print(f"    ... ({len(subs) - 10} more)")
                for i, sub in enumerate(subs[-3:], len(subs)-3):
                    print(f"    [{i}] {sub}")
        else:
            print("  sub_questions: None")

        # 查所有语文入库题的 sub_questions 数量
        rows = await conn.fetch("""
            SELECT qi.source_question_number, q.sub_questions, q.is_composite
            FROM questions q
            JOIN question_instances qi ON qi.question_id = q.id
            JOIN documents d ON d.id = qi.document_id
            WHERE d.subject = '语文'
            ORDER BY qi.source_question_number::int
        """)
        print(f"\n=== 语文全部入库题 sub_questions 统计 ===")
        for r in rows:
            qn = r['source_question_number']
            subs = r['sub_questions']
            sub_count = len(subs) if subs else 0
            is_comp = r['is_composite']
            print(f"  Q{qn} | composite={is_comp} | subs={sub_count}")

    finally:
        await conn.close()

asyncio.run(main())

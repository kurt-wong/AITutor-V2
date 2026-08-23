"""深度分析：Q22 子题数 130 爆炸的根因。

读取 L2 标注原始 JSON，检查 sub_questions 字段的实际内容。
"""
import asyncio, asyncpg, sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"

async def main():
    conn = await asyncpg.connect(DSN)
    try:
        # 语文文档
        row = await conn.fetchrow("""
            SELECT id, llm_annotated_markdown
            FROM documents WHERE subject = '语文' LIMIT 1
        """)
        doc_id = row['id']
        l2 = json.loads(row['llm_annotated_markdown'])
        questions = l2.get('questions', [])

        print(f"=== 语文 L2 标注详情（{len(questions)} 题） ===\n")

        for q in questions:
            qn = q.get('question_number')
            qt = q.get('question_type')
            is_comp = q.get('is_composite')
            stem_ids = q.get('stem_line_ids', [])
            opt_ids = q.get('options_line_ids', {})
            ans_ids = q.get('answer_line_ids', [])
            shared = q.get('shared_material_line_ids', [])
            subs = q.get('sub_questions', [])
            markers = q.get('stem_markers', [])

            print(f"--- Q{qn} ---")
            print(f"  type={qt}, composite={is_comp}")
            print(f"  stem_line_ids ({len(stem_ids)}): {stem_ids[:8]}{'...' if len(stem_ids)>8 else ''}")
            print(f"  options_line_ids: {opt_ids}")
            print(f"  answer_line_ids ({len(ans_ids)}): {ans_ids[:5]}{'...' if len(ans_ids)>5 else ''}")
            print(f"  shared_material_line_ids ({len(shared)}): {shared[:5]}{'...' if len(shared)>5 else ''}")
            print(f"  stem_markers ({len(markers)}): {markers[:3]}{'...' if len(markers)>3 else ''}")

            if subs:
                print(f"  sub_questions ({len(subs)}):")
                # 显示前 5 个和最后 2 个子题
                for i, sub in enumerate(subs[:5]):
                    print(f"    [{i}] qno={sub.get('qno')} type={sub.get('question_type')} "
                          f"stem_ids={sub.get('stem_line_ids', [])[:3]} "
                          f"answer={str(sub.get('answer', ''))[:30]}")
                if len(subs) > 7:
                    print(f"    ... ({len(subs) - 7} more) ...")
                    for i, sub in enumerate(subs[-2:], len(subs)-2):
                        print(f"    [{i}] qno={sub.get('qno')} type={sub.get('question_type')} "
                              f"stem_ids={sub.get('stem_line_ids', [])[:3]} "
                              f"answer={str(sub.get('answer', ''))[:30]}")
            print()

    finally:
        await conn.close()

asyncio.run(main())

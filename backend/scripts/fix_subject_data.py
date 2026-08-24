#!/usr/bin/env python3
"""修复空名 subject 数据（2026-08-25）。

背景：ingestion 的 _get_or_create_subject 查不到就创建，LLM 答案提取返回
空/非规范 subject 时创建了垃圾行。28 题（政治文档）指向空名 subject，另有
生物学/英语(A班)/高一物理 三个无题垃圾行。

修复：
1. 检查 28 题的知识点映射是否也被污染（subject_code 回退 MATH）
2. 28 题 subject_id 改指 canonical 政治
3. 清理无引用的垃圾 subject 行（先查 FK 引用再删）
"""
import asyncio
import io
import sys

import asyncpg

if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

EMPTY_SUBJECT = "449f8c13-de0f-4a62-9bca-f099553a1a99"
POLI_SUBJECT = "0181e66b-533d-458d-97f6-5aad9903f4e4"
JUNK_NAMES = ("生物学", "英语(a班)", "英语(A班)", "高一物理")


async def main():
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:15432/aitutors")
    try:
        # 0. 检查 28 题的知识点映射
        print("=== 0. 28 题的知识点映射（检查是否被污染）===")
        rows = await conn.fetch(
            "SELECT qk.knowledge_node_id, COUNT(*) AS n "
            "FROM question_knowledge qk "
            "JOIN questions q ON q.id = qk.question_id "
            "WHERE q.subject_id = $1 "
            "GROUP BY qk.knowledge_node_id ORDER BY n DESC LIMIT 10",
            EMPTY_SUBJECT,
        )
        for r in rows:
            node = await conn.fetchrow(
                "SELECT code, name, subject_id FROM knowledge_nodes WHERE id = $1",
                r["knowledge_node_id"],
            )
            print(f"  knowledge_node_id={r['knowledge_node_id']} n={r['n']} "
                  f"code={node['code']!r} name={node['name']!r}")
        total_qk = await conn.fetchval(
            "SELECT COUNT(*) FROM question_knowledge qk "
            "JOIN questions q ON q.id = qk.question_id WHERE q.subject_id = $1",
            EMPTY_SUBJECT,
        )
        print(f"  question_knowledge 总数: {total_qk}")

        # 1. 重新映射 28 题
        print("\n=== 1. 28 题 subject_id 改指 政治 ===")
        before = await conn.fetchval(
            "SELECT COUNT(*) FROM questions WHERE subject_id = $1", EMPTY_SUBJECT
        )
        await conn.execute(
            "UPDATE questions SET subject_id = $1 WHERE subject_id = $2",
            POLI_SUBJECT, EMPTY_SUBJECT,
        )
        after = await conn.fetchval(
            "SELECT COUNT(*) FROM questions WHERE subject_id = $1", EMPTY_SUBJECT
        )
        print(f"  更新 {before - after} 题（剩余指向空名: {after}）")

        # 2. 检查垃圾行引用
        print("\n=== 2. 垃圾 subject 行引用检查 ===")
        for name in JUNK_NAMES + ("",):
            subj = await conn.fetchrow(
                "SELECT id, name FROM subjects WHERE name = $1", name
            )
            if not subj:
                print(f"  {name!r}: 不存在")
                continue
            q = await conn.fetchval(
                "SELECT COUNT(*) FROM questions WHERE subject_id = $1", subj["id"]
            )
            node = await conn.fetchval(
                "SELECT COUNT(*) FROM knowledge_nodes WHERE subject_id = $1", subj["id"]
            )
            print(f"  {name!r} id={subj['id']}: questions={q} knowledge_nodes={node}")
            if q == 0 and node == 0:
                await conn.execute("DELETE FROM subjects WHERE id = $1", subj["id"])
                print(f"    → 已删除")
            else:
                print(f"    → 有引用，保留")

        # 3. 终态验证
        print("\n=== 3. 终态验证 ===")
        empty_left = await conn.fetchval(
            "SELECT COUNT(*) FROM questions WHERE subject_id = $1", EMPTY_SUBJECT
        )
        print(f"  空名 subject 的题数: {empty_left}（应为 0）")
        rows = await conn.fetch(
            "SELECT s.name, COUNT(q.id) AS n FROM questions q "
            "JOIN subjects s ON s.id = q.subject_id GROUP BY s.name ORDER BY n DESC"
        )
        for r in rows:
            print(f"  {r['name']!r}: {r['n']}")
    finally:
        await conn.close()


asyncio.run(main())

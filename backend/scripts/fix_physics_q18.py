#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据修复：物理 Q18（3）DB 答案摘要 → 与答案区一致的完整表述。

背景：Q18（受力分析图题）DB answer 为 L2 精简版
"（1）见解析 （2）1.5N （3）夹角增大，拉力增大"。
- (1) 答案在受力分析图中（答案区该子部分无文本，只有分值注记），
  "见解析"是正确占位（verifier 已支持剔除"见解析"子部分后核对其余部分）。
- (3) 答案区完整表述为 "F增大，θ增大，轻绳与竖直方向夹角增大，轻绳拉力T增大"，
  DB 摘要 "夹角增大，拉力增大" 不是答案区子串 → structured_partial。
  把 (3) 改为答案区原文一致表述，使 verifier 可验证。
幂等：目标 answer 已为修复值时跳过。
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "test" / "scripts"))

import asyncpg  # noqa: E402

TARGET_ANSWER = (
    "（1）见解析 （2）1.5N "
    "（3）F增大，\u03b8增大，轻绳与竖直方向夹角增大，轻绳拉力T增大"
)


async def main() -> None:
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:15432/aitutors")
    try:
        doc = await conn.fetchrow(
            "SELECT id, filename FROM documents WHERE subject=$1 AND processing_status='completed' ORDER BY created_at DESC LIMIT 1",
            "物理",
        )
        if not doc:
            print("物理: 无 completed 文档")
            return
        row = await conn.fetchrow(
            """
            SELECT q.id, q.answer FROM questions q
            JOIN question_instances qi ON qi.question_id = q.id
            WHERE qi.document_id = $1 AND qi.source_question_number = '18'
            """,
            str(doc["id"]),
        )
        if not row:
            print("物理 Q18: 缺库")
            return
        cur = str(row["answer"] or "")
        if cur == TARGET_ANSWER:
            print(f"物理 Q18 已是目标答案，跳过（{doc['filename']}）")
            return
        await conn.execute("UPDATE questions SET answer=$1 WHERE id=$2", TARGET_ANSWER, row["id"])
        print(f"物理 Q18 已更新（{doc['filename']}）:")
        print(f"  OLD: {cur!r}")
        print(f"  NEW: {TARGET_ANSWER!r}")
    finally:
        await conn.close()


asyncio.run(main())

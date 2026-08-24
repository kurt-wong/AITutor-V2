#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据修复：语文朝阳 Q17（用户审核通过，方案 A）。

- stem 截断：去掉 "\n0\n四、本大题..." 起的串题部分（保留 P5L014-P5L021 默写 prompt）。
- status → approved，review_reason → NULL（答案已与 PDF 答案区一致，假冲突）。
幂等：仅当 stem 含串题标记才截断；已 approved 则跳过。
"""
import asyncio
import sys

import asyncpg

DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"

# 串题起始标记：OCR 噪声行 "0" + 下一 section 标题
BOUNDARY = "\n0\n四、本大题"


async def main() -> None:
    conn = await asyncpg.connect(DSN)
    try:
        rows = await conn.fetch(
            """
            SELECT q.id, q.stem, q.answer, q.status, q.review_reason
            FROM questions q
            JOIN question_instances qi ON qi.question_id = q.id
            JOIN documents d ON d.id = qi.document_id
            WHERE d.subject = '语文'
              AND qi.source_question_number::int = 17
            """
        )
        print(f"命中 Q17 行数: {len(rows)}")
        for r in rows:
            qid = r["id"]
            stem = r["stem"] or ""
            idx = stem.find(BOUNDARY)
            if idx < 0:
                print(f"Q17({qid}): 无串题标记，跳过截断；status={r['status']} reason={r['review_reason']!r}")
                continue
            new_stem = stem[:idx].rstrip()
            print(f"Q17({qid}): stem {len(stem)} -> {len(new_stem)} 字符")
            print(f"  新 stem 末 60: ...{new_stem[-60:]!r}")
            await conn.execute(
                """
                UPDATE questions SET stem = $1, status = 'approved', review_reason = NULL
                WHERE id = $2
                """,
                new_stem,
                qid,
            )
            print(f"Q17({qid}): 已截断 + approved + 清 review_reason")
    finally:
        await conn.close()


asyncio.run(main())

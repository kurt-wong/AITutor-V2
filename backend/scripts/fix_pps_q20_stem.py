#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据修复：PPS 物理 Q20 stem 真膨胀截断（同 mimo 版处理）。

PPS 重跑 Q20 stem 1231 字符，尾部混入"自主命制试题"整节（Q4/Q7 内容 +
LLM 注释），截断到"自主命制试题"前（685 字符，Q20 自己的拖把/传送带/
字典三小问完整保留）→ approved。
幂等：仅当 stem 含"自主命制"或"本部分共两小题"时截断。
"""
import asyncio
import sys
from pathlib import Path

import asyncpg

DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"


async def main() -> None:
    conn = await asyncpg.connect(DSN)
    try:
        doc = await conn.fetchrow(
            "SELECT id FROM documents WHERE subject='物理' AND processing_status='completed' ORDER BY created_at DESC LIMIT 1"
        )
        row = await conn.fetchrow(
            """
            SELECT q.id, q.stem FROM questions q
            JOIN question_instances qi ON qi.question_id = q.id
            WHERE qi.document_id = $1 AND qi.source_question_number = '20'
            """,
            str(doc["id"]),
        )
        if not row:
            print("DB 无物理 Q20")
            return
        stem = row["stem"] or ""
        cut = stem.find("自主命制")
        if cut < 0:
            cut = stem.find("本部分共两小题")
        if cut < 0:
            print("Q20 stem 无混入标记，跳过")
            return
        new_stem = stem[:cut].rstrip()
        print(f"Q20 stem: {len(stem)} -> {len(new_stem)} 字符")
        print(f"截断后尾部: {new_stem[-80:]!r}")
        await conn.execute(
            "UPDATE questions SET stem = $1, status = 'approved', review_reason = NULL WHERE id = $2",
            new_stem, row["id"],
        )
        print("Q20: 已截断 + approved")
    finally:
        await conn.close()


asyncio.run(main())

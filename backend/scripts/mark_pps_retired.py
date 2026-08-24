#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""临时处理：PPS 语文/化学文档标记 superseded（保留数据，mimo 版恢复为基线）。

2026-08-25 PPS 全科重跑结论：语文（L2 仅 8/24 题）、化学（21/26，表格
选项丢失）PPS 明显退化；用户决策待定。此处将两份 PPS 新文档标记
processing_status='superseded'（非 completed），e2e 报告选最新 completed
→ mimo 版恢复基线。数据不删除，可随时回滚状态。
"""
import asyncio
import sys
from pathlib import Path

import asyncpg

DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"


async def main() -> None:
    conn = await asyncpg.connect(DSN)
    try:
        # 找各科最新 completed 文档（PPS 重跑版）与次新（mimo 版）
        for subject in ("语文", "化学"):
            docs = await conn.fetch(
                """
                SELECT id, created_at, processing_status FROM documents
                WHERE subject = $1 ORDER BY created_at DESC LIMIT 2
                """,
                subject,
            )
            if len(docs) < 2:
                print(f"{subject}: 文档不足 2 份（{[(str(d['id'])[:8], d['processing_status']) for d in docs]}）")
                continue
            pps_doc, mimo_doc = docs[0], docs[1]
            print(f"{subject}: 最新={str(pps_doc['id'])[:8]} ({pps_doc['processing_status']}) 次新={str(mimo_doc['id'])[:8]} ({mimo_doc['processing_status']})")
            if pps_doc["processing_status"] == "completed" and mimo_doc["processing_status"] == "completed":
                await conn.execute(
                    "UPDATE documents SET processing_status = 'superseded' WHERE id = $1",
                    pps_doc["id"],
                )
                print(f"  {subject}: PPS 文档已标记 superseded（mimo 版恢复基线）")
            else:
                print(f"  {subject}: 状态不满足（可能已处理）")
    finally:
        await conn.close()


asyncio.run(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""化学回退 mimo：PPS/VL 新文档标记 superseded（保留数据）。

VL 化学 15/26 比 PPS 21/26 更差——Paddle 系（PPS/VL）对化学表格选项
均不适用（表格内选项结构识别差），mimo 26/26 是唯一完美选项。
标记 PPS/VL 化学文档 superseded，mimo 恢复为最新 completed。
"""
import asyncio
import sys
from pathlib import Path

import asyncpg

DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"


async def main() -> None:
    conn = await asyncpg.connect(DSN)
    try:
        docs = await conn.fetch(
            """
            SELECT id, created_at, processing_status FROM documents
            WHERE subject = '化学' ORDER BY created_at DESC LIMIT 4
            """
        )
        print("化学文档（新→旧）:")
        for d in docs:
            print(f"  {d['created_at']} {d['processing_status']} {str(d['id'])[:8]}")
        # 最新 completed 且非 mimo（PPS/VL 版）标记 superseded，直到遇到 mimo 版
        retired = 0
        for d in docs:
            if d["processing_status"] != "completed":
                continue
            # 保留最早的 completed（mimo 版），其余 superseded
            await conn.execute(
                "UPDATE documents SET processing_status = 'superseded' WHERE id = $1",
                d["id"],
            )
            retired += 1
            print(f"  标记 superseded: {str(d['id'])[:8]}")
            # 只回退到 mimo 版（第 2 个 completed 为止）
            if retired >= 1:
                break
    finally:
        await conn.close()


asyncio.run(main())

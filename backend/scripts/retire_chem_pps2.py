#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""继续回退：标记 PPS 版化学文档 superseded（保留 mimo b6ca9f97）。"""
import asyncio

import asyncpg

DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"


async def main() -> None:
    conn = await asyncpg.connect(DSN)
    try:
        rows = await conn.fetch(
            """
            SELECT id, created_at, processing_status FROM documents
            WHERE subject = '化学' AND processing_status = 'completed'
            ORDER BY created_at DESC
            """
        )
        for r in rows:
            # 保留最早的（mimo 版），其余 superseded
            if r["id"] != rows[-1]["id"]:
                await conn.execute(
                    "UPDATE documents SET processing_status = 'superseded' WHERE id = $1",
                    r["id"],
                )
                print(f"superseded: {str(r['id'])[:8]} ({r['created_at']})")
            else:
                print(f"保留 mimo: {str(r['id'])[:8]} ({r['created_at']})")
    finally:
        await conn.close()


asyncio.run(main())

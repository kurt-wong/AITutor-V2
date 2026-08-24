#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""临时：PVL 化学文档改回 completed（验证修复效果）。"""
import asyncio

import asyncpg

DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"
DOC_ID = "804f2396-47b9-4837-aa7e-050b511e497a"


async def main() -> None:
    conn = await asyncpg.connect(DSN)
    try:
        r = await conn.fetchrow(
            "SELECT processing_status FROM documents WHERE id = $1", DOC_ID
        )
        print(f"当前状态: {r['processing_status']}")
        if r["processing_status"] != "completed":
            await conn.execute(
                "UPDATE documents SET processing_status = 'completed' WHERE id = $1", DOC_ID
            )
            print("已改回 completed")
    finally:
        await conn.close()


asyncio.run(main())

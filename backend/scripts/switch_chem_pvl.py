#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""化学数据源切换：PVL(804f2396) completed、mimo(b6ca9f97) superseded。"""
import asyncio

import asyncpg

DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"


async def main() -> None:
    conn = await asyncpg.connect(DSN)
    try:
        # PVL 改回 completed（若 superseded）
        await conn.execute(
            "UPDATE documents SET processing_status = 'completed' WHERE id = '804f2396-47b9-4837-aa7e-050b511e497a'"
        )
        print("PVL 化学: completed")
        # mimo 标记 superseded
        await conn.execute(
            "UPDATE documents SET processing_status = 'superseded' WHERE id = 'b6ca9f97-0000-0000-0000-000000000000' OR (subject='化学' AND id <> '804f2396-47b9-4837-aa7e-050b511e497a' AND processing_status='completed')"
        )
        rows = await conn.fetch(
            "SELECT id, processing_status FROM documents WHERE subject='化学' ORDER BY created_at DESC"
        )
        for r in rows:
            print(f"  {str(r['id'])[:8]} {r['processing_status']}")
    finally:
        await conn.close()


asyncio.run(main())

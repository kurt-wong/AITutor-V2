#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""清理：后端重启中断卡在 running 的旧任务（57db59bb / 1bf05505）→ failed。"""
import asyncio

import asyncpg

DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"
STUCK = [
    "57db59bb-d81b-4245-aafe-e857f1ddc1b3",
    "1bf05505-db48-485f-96ee-ffcea2cc94db",
]


async def main() -> None:
    conn = await asyncpg.connect(DSN)
    try:
        for tid in STUCK:
            r = await conn.fetchrow(
                "SELECT id, status, task_type FROM background_tasks WHERE id = $1", tid
            )
            if not r:
                print(f"{tid[:8]}: 不存在")
                continue
            if r["status"] != "running":
                print(f"{tid[:8]}: status={r['status']}，无需清理")
                continue
            await conn.execute(
                """
                UPDATE background_tasks
                SET status = 'failed', error_detail = '清理：后端重启中断（OCR 策略变更）',
                    updated_at = now()
                WHERE id = $1
                """,
                tid,
            )
            print(f"{tid[:8]}: running -> failed（清理完成）")
    finally:
        await conn.close()


asyncio.run(main())

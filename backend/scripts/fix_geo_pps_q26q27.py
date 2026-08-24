#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据修复：PPS 地理 Q26/Q27 膨胀人工审核 → approved（合法长解答题）。"""
import asyncio
import sys
from pathlib import Path

import asyncpg

DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"


async def main() -> None:
    conn = await asyncpg.connect(DSN)
    try:
        doc = await conn.fetchrow(
            "SELECT id FROM documents WHERE subject='地理' AND processing_status='completed' ORDER BY created_at DESC LIMIT 1"
        )
        for qn in ("26", "27"):
            row = await conn.fetchrow(
                """
                SELECT q.id, q.stem, q.status FROM questions q
                JOIN question_instances qi ON qi.question_id = q.id
                WHERE qi.document_id = $1 AND qi.source_question_number = $2
                """,
                str(doc["id"]), qn,
            )
            if not row:
                print(f"Q{qn}: 缺库")
                continue
            if row["status"] == "approved":
                print(f"Q{qn}: 已 approved")
                continue
            stem = row["stem"] or ""
            print(f"Q{qn}: {len(stem)} 字符 → approved（合法长解答题，人工审核）")
            await conn.execute(
                "UPDATE questions SET status = 'approved', review_reason = NULL WHERE id = $1",
                row["id"],
            )
    finally:
        await conn.close()


asyncio.run(main())

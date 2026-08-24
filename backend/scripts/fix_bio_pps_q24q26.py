#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据修复：生物 PPS——Q26 stem 截断（串入答案区）+ Q24 膨胀审核 approve。"""
import asyncio
import sys
from pathlib import Path

import asyncpg

DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"


async def main() -> None:
    conn = await asyncpg.connect(DSN)
    try:
        doc = await conn.fetchrow(
            "SELECT id FROM documents WHERE subject='生物' AND processing_status='completed' ORDER BY created_at DESC LIMIT 1"
        )
        doc_id = str(doc["id"])

        # Q26 截断
        q26 = await conn.fetchrow(
            """
            SELECT q.id, q.stem FROM questions q
            JOIN question_instances qi ON qi.question_id = q.id
            WHERE qi.document_id = $1 AND qi.source_question_number = '26'
            """,
            doc_id,
        )
        if q26:
            stem = q26["stem"] or ""
            cut = stem.find("A.胚胎细胞中存在与细胞凋亡有关的基因")
            if cut > 0:
                new_stem = stem[:cut].rstrip()
                print(f"Q26 stem: {len(stem)} -> {len(new_stem)}（截断答案区串入）")
                await conn.execute(
                    "UPDATE questions SET stem = $1, status = 'approved', review_reason = NULL WHERE id = $2",
                    new_stem, q26["id"],
                )
            else:
                print("Q26 无答案区串入标记")

        # Q24 approve（合法材料题）
        q24 = await conn.fetchrow(
            """
            SELECT q.id, q.stem, q.status FROM questions q
            JOIN question_instances qi ON qi.question_id = q.id
            WHERE qi.document_id = $1 AND qi.source_question_number = '24'
            """,
            doc_id,
        )
        if q24 and q24["status"] != "approved":
            print(f"Q24 stem {len(q24['stem'] or '')} 字符 → approved（光合作用材料题，人工审核）")
            await conn.execute(
                "UPDATE questions SET status = 'approved', review_reason = NULL WHERE id = $1",
                q24["id"],
            )
    finally:
        await conn.close()


asyncio.run(main())

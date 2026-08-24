#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q21 stem 并入完整材料（含图例）。"""
import asyncio
import json
import sys
from pathlib import Path

import asyncpg

DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"
Q21_STEM = (
    "图(a)和图(b)分别为内蒙古高原与东南丘陵两处采样点的土壤剖面(0-80厘米)示意图。"
    "读图，完成下面小题。()(q)图例一有机层腐殖质层淋溶层淀积层"
    "21.与图(b)相比，图(a)所示土壤剖面（）"
)
Q21_OPTIONS = [
    {"label": "A", "text": "土层数量更多"},
    {"label": "B", "text": "有机层缺失"},
    {"label": "C", "text": "腐殖质层更厚"},
    {"label": "D", "text": "淀积层分布更浅"},
]


async def main() -> None:
    conn = await asyncpg.connect(DSN)
    try:
        doc = await conn.fetchrow(
            "SELECT id FROM documents WHERE subject='地理' AND processing_status='completed' ORDER BY created_at DESC LIMIT 1"
        )
        q21 = await conn.fetchrow(
            """
            SELECT q.id FROM questions q
            JOIN question_instances qi ON qi.question_id = q.id
            WHERE qi.document_id = $1 AND qi.source_question_number = '21'
            """,
            str(doc["id"]),
        )
        if q21:
            await conn.execute(
                "UPDATE questions SET stem = $1, options = $2::jsonb WHERE id = $3",
                Q21_STEM, json.dumps(Q21_OPTIONS, ensure_ascii=False), q21["id"],
            )
            print("Q21 stem 已并入完整材料（含图例）")
    finally:
        await conn.close()


asyncio.run(main())

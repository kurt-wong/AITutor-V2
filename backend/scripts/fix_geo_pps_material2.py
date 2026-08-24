#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""补处理：删幻选题（含 question_images）+ Q21 材料并入。"""
import asyncio
import json
import sys
from pathlib import Path

import asyncpg

DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"
Q21_STEM = (
    "图(a)和图(b)分别为内蒙古高原与东南丘陵两处采样点的土壤剖面(0-80厘米)示意图。"
    "读图，完成下面小题。21.与图(b)相比，图(a)所示土壤剖面（）"
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
        doc_id = str(doc["id"])

        # 1. 剩余幻选题（23/24/25）
        rows = await conn.fetch(
            """
            SELECT qi.id AS inst_id, q.id AS qid FROM question_instances qi
            JOIN questions q ON q.id = qi.question_id
            WHERE qi.document_id = $1 AND qi.source_question_number::int IN (23, 24, 25)
            """,
            doc_id,
        )
        for r in rows:
            await conn.execute("DELETE FROM question_instances WHERE id = $1", r["inst_id"])
            await conn.execute("DELETE FROM question_images WHERE question_id = $1", r["qid"])
            cnt = await conn.fetchval(
                "SELECT count(*) FROM question_instances WHERE question_id = $1", r["qid"]
            )
            if cnt == 0:
                await conn.execute("DELETE FROM questions WHERE id = $1", r["qid"])
                print(f"删幻选题 question {str(r['qid'])[:8]}")
            else:
                print(f"instance {str(r['inst_id'])[:8]} 已删，question 仍有 {cnt} 引用")

        # 2. Q21 材料并入
        q21 = await conn.fetchrow(
            """
            SELECT q.id, q.stem FROM questions q
            JOIN question_instances qi ON qi.question_id = q.id
            WHERE qi.document_id = $1 AND qi.source_question_number = '21'
            """,
            doc_id,
        )
        if q21 and "图(a)和图(b)分别为" not in (q21["stem"] or ""):
            await conn.execute(
                "UPDATE questions SET stem = $1, options = $2::jsonb WHERE id = $3",
                Q21_STEM, json.dumps(Q21_OPTIONS, ensure_ascii=False), q21["id"],
            )
            print("Q21 stem 已并入材料")
        else:
            print(f"Q21 stem 状态: 已含材料={'图(a)和图(b)分别为' in (q21 or {}).get('stem') or '' if q21 else '无'}")
    finally:
        await conn.close()


asyncio.run(main())

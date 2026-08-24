#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据修复：PPS 地理 Q21 stem/options/answer 修正（材料误作题干 → 真实题干）。"""
import asyncio
import json
import sys
from pathlib import Path

import asyncpg

DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"

Q21_STEM = "21.与图(b)相比，图(a)所示土壤剖面（）"
Q21_OPTIONS = [
    {"label": "A", "text": "土层数量更多"},
    {"label": "B", "text": "有机层缺失"},
    {"label": "C", "text": "腐殖质层更厚"},
    {"label": "D", "text": "淀积层分布更浅"},
]
Q21_MARKER = "21.与图(b)相比，图(a)所示土壤剖面（）"


async def main() -> None:
    conn = await asyncpg.connect(DSN)
    try:
        doc = await conn.fetchrow(
            "SELECT id, llm_annotated_markdown FROM documents WHERE subject='地理' AND processing_status='completed' ORDER BY created_at DESC LIMIT 1"
        )
        row = await conn.fetchrow(
            """
            SELECT q.id, q.stem FROM questions q
            JOIN question_instances qi ON qi.question_id = q.id
            WHERE qi.document_id = $1 AND qi.source_question_number = '21'
            """,
            str(doc["id"]),
        )
        if not row:
            print("无地理 Q21")
            return
        if "21.与图(b)相比" not in (row["stem"] or ""):
            await conn.execute(
                "UPDATE questions SET stem = $1, options = $2::jsonb, answer = 'C', status = 'approved', review_reason = NULL WHERE id = $3",
                Q21_STEM, json.dumps(Q21_OPTIONS, ensure_ascii=False), row["id"],
            )
            print(f"Q21 stem/options 已修正（原 stem: {(row['stem'] or '')[:40]}...）")
        else:
            print("Q21 stem 已正确")

        # L2 marker
        l2 = json.loads(doc["llm_annotated_markdown"] or "{}")
        changed = False
        for q in l2.get("questions", []):
            if str(q.get("question_number")) == "21":
                q["stem_start_marker"] = Q21_MARKER
                changed = True
        if changed:
            await conn.execute(
                "UPDATE documents SET llm_annotated_markdown = $1 WHERE id = $2",
                json.dumps(l2, ensure_ascii=False),
                str(doc["id"]),
            )
            print("L2 Q21 marker 已修正")
    finally:
        await conn.close()


asyncio.run(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据修复：生物 PPS L2 Q26 stem_line_ids 修正（P4L003-007 → P8L002-014 材料）。"""
import asyncio
import json
import sys
from pathlib import Path

import asyncpg

DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"
NEW_STEM_IDS = [
    "P8L002", "P8L003", "P8L004", "P8L005", "P8L006", "P8L007",
    "P8L008", "P8L009", "P8L010", "P8L011", "P8L012", "P8L013", "P8L014",
]


async def main() -> None:
    conn = await asyncpg.connect(DSN)
    try:
        doc = await conn.fetchrow(
            "SELECT id, llm_annotated_markdown FROM documents WHERE subject='生物' AND processing_status='completed' ORDER BY created_at DESC LIMIT 1"
        )
        l2 = json.loads(doc["llm_annotated_markdown"] or "{}")
        changed = False
        for q in l2.get("questions", []):
            if str(q.get("question_number")) == "26":
                old = q.get("stem_line_ids") or []
                if old and "P8L002" not in old:
                    q["stem_line_ids"] = list(NEW_STEM_IDS)
                    changed = True
                    print(f"L2 Q26 stem_line_ids: {old} -> {NEW_STEM_IDS[:3]}...")
        if changed:
            await conn.execute(
                "UPDATE documents SET llm_annotated_markdown = $1 WHERE id = $2",
                json.dumps(l2, ensure_ascii=False),
                str(doc["id"]),
            )
            print("L2 Q26 stem_line_ids 已修正")
    finally:
        await conn.close()


asyncio.run(main())

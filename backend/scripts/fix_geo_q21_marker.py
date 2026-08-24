#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据修复：地理 L2 Q21 stem_start_marker 修正（幻造 marker → 真实题干）。"""
import asyncio
import json
import sys
from pathlib import Path

import asyncpg

DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"
MARKER = "21.与图(b)相比，图(a)所示土壤剖面（）"


async def main() -> None:
    conn = await asyncpg.connect(DSN)
    try:
        doc = await conn.fetchrow(
            "SELECT id, llm_annotated_markdown FROM documents WHERE subject='地理' AND processing_status='completed' ORDER BY created_at DESC LIMIT 1"
        )
        l2 = json.loads(doc["llm_annotated_markdown"] or "{}")
        changed = False
        for q in l2.get("questions", []):
            if str(q.get("question_number")) == "21":
                cur = q.get("stem_start_marker") or ""
                print(f"Q21 当前 marker: {cur[:40]!r}")
                q["stem_start_marker"] = MARKER
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

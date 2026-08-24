#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据修复：历史 PPS L2 Q37 stem_start_marker 修正（标注失败垃圾标记 → 真实题干）。"""
import asyncio
import json
import sys
from pathlib import Path

import asyncpg

DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"
MARKER = "37.中国共产党成立以来，不断探索中国革命和建设"


async def main() -> None:
    conn = await asyncpg.connect(DSN)
    try:
        doc = await conn.fetchrow(
            "SELECT id, llm_annotated_markdown FROM documents WHERE subject='历史' AND processing_status='completed' ORDER BY created_at DESC LIMIT 1"
        )
        l2 = json.loads(doc["llm_annotated_markdown"] or "{}")
        changed = False
        for q in l2.get("questions", []):
            if str(q.get("question_number")) == "37":
                cur = q.get("stem_start_marker") or ""
                print(f"Q37 当前 marker: {cur[:40]!r}")
                q["stem_start_marker"] = MARKER
                changed = True
        if changed:
            await conn.execute(
                "UPDATE documents SET llm_annotated_markdown = $1 WHERE id = $2",
                json.dumps(l2, ensure_ascii=False),
                str(doc["id"]),
            )
            print("L2 Q37 marker 已修正")
        else:
            print("L2 无 Q37")
    finally:
        await conn.close()


asyncio.run(main())

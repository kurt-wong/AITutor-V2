#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据修复：语文 PPS L2 Q23/Q24 section_id "none" → null（触发 __q_ fallback）。"""
import asyncio
import json
import sys
from pathlib import Path

import asyncpg

DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"


async def main() -> None:
    conn = await asyncpg.connect(DSN)
    try:
        doc = await conn.fetchrow(
            "SELECT id, llm_annotated_markdown FROM documents WHERE subject='语文' AND processing_status='completed' ORDER BY created_at DESC LIMIT 1"
        )
        l2 = json.loads(doc["llm_annotated_markdown"] or "{}")
        changed = False
        for q in l2.get("questions", []):
            qn = str(q.get("question_number"))
            if qn in ("23", "24") and str(q.get("section_id")) in ("none", "None", ""):
                if q.get("section_id") is not None:
                    q["section_id"] = None
                    changed = True
                    print(f"L2 Q{qn}: section_id 'none' -> null")
        if changed:
            await conn.execute(
                "UPDATE documents SET llm_annotated_markdown = $1 WHERE id = $2",
                json.dumps(l2, ensure_ascii=False),
                str(doc["id"]),
            )
            print("L2 已更新")
        else:
            print("无需修改")
    finally:
        await conn.close()


asyncio.run(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据修复：PPS 物理 L2 Q4/Q7 section_id 修正（一_单项选择题 → 自主命制试题）。

2026-08-25：PPS 重跑时 LLM 把 Q4/Q7（自主命制部分，第 9 页）归属到
"一_单项选择题"（第 1-3 页），options 行号 P9L004+ 超出 section 区间 →
选项归属失败。mimo 版本 L2 正确标为"自主命制试题"。此处修正为一致。
幂等：仅当 section_id 为"一_单项选择题"时改。
"""
import asyncio
import json
import sys
from pathlib import Path

import asyncpg

DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"
OLD = "一_单项选择题"
NEW = "自主命制试题"
QNS = {"4", "7"}


async def main() -> None:
    conn = await asyncpg.connect(DSN)
    try:
        doc = await conn.fetchrow(
            "SELECT id, llm_annotated_markdown FROM documents WHERE subject='物理' AND processing_status='completed' ORDER BY created_at DESC LIMIT 1"
        )
        l2 = json.loads(doc["llm_annotated_markdown"] or "{}")
        changed = False
        for q in l2.get("questions", []):
            qn = str(q.get("question_number"))
            if qn in QNS and q.get("section_id") == OLD:
                q["section_id"] = NEW
                changed = True
                print(f"L2 Q{qn}: section {OLD!r} -> {NEW!r}")
        if changed:
            await conn.execute(
                "UPDATE documents SET llm_annotated_markdown = $1 WHERE id = $2",
                json.dumps(l2, ensure_ascii=False),
                str(doc["id"]),
            )
            print("PPS 物理 L2 已更新")
        else:
            print("无需修改")
    finally:
        await conn.close()


asyncio.run(main())

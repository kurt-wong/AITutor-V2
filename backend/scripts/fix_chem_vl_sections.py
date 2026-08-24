#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据修复：PVL 化学 L2 Q12/Q13 section 归属修正（粗盐提纯_12_13 → 第一部分_选择题）。

根因：Q12/Q13 是共享材料（粗盐提纯）选择题，LLM 给了自创 section
"粗盐提纯_12_13"（第 2 页）→ 第一部分_选择题 id_max 被提前到第 2 页 →
Q14-21（第 3/4 页）行号全部误判越界（PVL 版 15/26 的真因，非 OCR）。
"""
import asyncio
import json
import sys
from pathlib import Path

import asyncpg

DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"
DOC_ID = "804f2396-47b9-4837-aa7e-050b511e497a"
OLD = "粗盐提纯_12_13"
NEW = "第一部分_选择题"


async def main() -> None:
    conn = await asyncpg.connect(DSN)
    try:
        doc = await conn.fetchrow(
            "SELECT llm_annotated_markdown FROM documents WHERE id = $1", DOC_ID
        )
        if not doc:
            print("文档不存在")
            return
        l2 = json.loads(doc["llm_annotated_markdown"] or "{}")
        changed = False
        for q in l2.get("questions", []):
            qn = str(q.get("question_number"))
            if qn in ("12", "13") and q.get("section_id") == OLD:
                q["section_id"] = NEW
                changed = True
                print(f"L2 Q{qn}: section {OLD!r} -> {NEW!r}")
        if changed:
            await conn.execute(
                "UPDATE documents SET llm_annotated_markdown = $1 WHERE id = $2",
                json.dumps(l2, ensure_ascii=False),
                DOC_ID,
            )
            print("L2 已更新")
        else:
            print("无需修改")
    finally:
        await conn.close()


asyncio.run(main())

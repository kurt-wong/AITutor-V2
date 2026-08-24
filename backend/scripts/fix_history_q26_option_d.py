#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据修复：历史 Q26 选项 D 缺失（用户按序修复任务④）。

根因：mimo OCR 漏识别 Q26 选项 D（OCR 里 C 后直接接 Q27），LLM 标注/
切片得 D.text 为空。pdf_raw/native 源中 D 真实存在：
"D.白话文在全国逐渐普及开来"。补回并转 approved。
幂等：仅当 D.text 为空时补。
"""
import asyncio
import json
import sys
from pathlib import Path

import asyncpg

DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"

D_TEXT = "白话文在全国逐渐普及开来"


async def main() -> None:
    conn = await asyncpg.connect(DSN)
    try:
        doc = await conn.fetchrow(
            """
            SELECT id FROM documents
            WHERE subject = '历史' AND processing_status = 'completed'
            ORDER BY created_at DESC LIMIT 1
            """
        )
        row = await conn.fetchrow(
            """
            SELECT q.id, q.options, q.status FROM questions q
            JOIN question_instances qi ON qi.question_id = q.id
            WHERE qi.document_id = $1 AND qi.source_question_number = '26'
            """,
            str(doc["id"]),
        )
        if not row:
            print("DB 无历史 Q26")
            return
        opts = row["options"] or []
        if isinstance(opts, str):
            opts = json.loads(opts) if opts else []
        d = next((o for o in opts if str(o.get("label", "")).upper() == "D"), None)
        if d is None:
            print("options 中无 D 条目")
            return
        if (d.get("text") or "").strip():
            print(f"D.text 已有内容: {d['text'][:40]!r}，跳过")
            return
        d["text"] = D_TEXT
        await conn.execute(
            "UPDATE questions SET options = $1::jsonb, status = 'approved', review_reason = NULL WHERE id = $2",
            json.dumps(opts, ensure_ascii=False),
            row["id"],
        )
        print(f"Q26 D.text 已补: {D_TEXT!r}，status -> approved")
    finally:
        await conn.close()


asyncio.run(main())

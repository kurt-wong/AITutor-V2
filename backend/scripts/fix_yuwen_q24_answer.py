#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据修复：语文 Q24 作文答案回填（用户按序修复任务③）。

DB answer 为残缺的 "例文：\n【答案】例文："（只截到标签，缺正文）。
答案区（native）从 "24.【答案】例文：" 到末尾是完整教师版答案
（两篇例文 + 详解 + 立意指导，共 4284 字符）。回填为完整内容。
幂等：当前 answer 已是完整内容（长度 > 1000）则跳过。
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "test" / "scripts"))
import asyncpg  # noqa: E402
import answer_verifier as AV  # noqa: E402

DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"


async def main() -> None:
    conn = await asyncpg.connect(DSN)
    try:
        doc = await conn.fetchrow(
            """
            SELECT id, native_markdown FROM documents
            WHERE subject = '语文' AND processing_status = 'completed'
            ORDER BY created_at DESC LIMIT 1
            """
        )
        doc_id = str(doc["id"])
        sec = AV.answer_section(doc["native_markdown"] or "")
        pos = sec.find("24.")
        if pos < 0:
            print("答案区未找到 24.")
            return
        # 从 "24.【答案】例文：" 之后开始（去掉 "24." 前缀），保留完整内容
        full = sec[pos:]
        # 去掉行首 "24." 前缀
        import re
        full = re.sub(r"^24\s*[.．]", "", full, count=1).lstrip("\n")
        print(f"提取答案长度: {len(full)}")

        row = await conn.fetchrow(
            """
            SELECT q.id, q.answer FROM questions q
            JOIN question_instances qi ON qi.question_id = q.id
            WHERE qi.document_id = $1 AND qi.source_question_number = '24'
            """,
            doc_id,
        )
        if not row:
            print("DB 无 Q24")
            return
        cur = row["answer"] or ""
        if len(cur) > 1000:
            print(f"Q24 当前答案已完整（{len(cur)} 字符），跳过")
            return
        print(f"Q24 当前答案（{len(cur)} 字符）: {cur[:80]!r}")
        await conn.execute("UPDATE questions SET answer = $1 WHERE id = $2", full, row["id"])
        print("Q24 答案已回填")
    finally:
        await conn.close()


asyncio.run(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据修复：膨胀边界审核（用户按序修复任务⑤）。

逐题人工审核结论（2026-08-25）：
- 物理 Q20（1598）：真膨胀——stem 尾部混入"自主命制试题"整节（Q4/Q7 完整内容 +
  mimo 幻觉标题 + LLM 注释"注：图片占位符…"）。截断到 "自主命制试题" 前
  （Q20 自己的拖把/传送带/字典三小问完整保留，863 字符）→ approved。
- 化学 Q23/Q24、地理 Q26：合法长解答题（多小问/化学方程式/HTML 实验表格），
  无大题标题混入、无其他 section 内容 → approved（人工判定，gate 无 section
  上下文无法区分，属已知口径限制）。
- 语文 Q23：非膨胀（391 字符），answer_conflict 为假冲突（两次重灌答案 compact
  完全一致，BUG-026 修复前的空白差异残留）→ 清标记 approved。

幂等：物理 Q20 仅当含"自主命制试题"时截断；其余仅当 status=reviewing 时转 approved。
"""
import asyncio
import json
import sys
from pathlib import Path

import asyncpg

DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"

APPROVE_PLAN = [
    ("化学", "23", "合法长解答题（氧化还原多小问，人工审核）"),
    ("化学", "24", "合法长解答题（实验探究含 HTML 表格，人工审核）"),
    ("地理", "26", "合法长解答题（读图+统计表，人工审核）"),
    ("语文", "23", "answer_conflict 假冲突（两次重灌答案 compact 一致）"),
]


async def main() -> None:
    conn = await asyncpg.connect(DSN)
    try:
        # ---- 物理 Q20 截断 ----
        pdoc = await conn.fetchrow(
            "SELECT id FROM documents WHERE subject='物理' AND processing_status='completed' ORDER BY created_at DESC LIMIT 1"
        )
        q20 = await conn.fetchrow(
            """
            SELECT q.id, q.stem FROM questions q
            JOIN question_instances qi ON qi.question_id = q.id
            WHERE qi.document_id = $1 AND qi.source_question_number = '20'
            """,
            str(pdoc["id"]),
        )
        if q20:
            stem = q20["stem"] or ""
            cut = stem.find("自主命制")
            if cut > 0:
                new_stem = stem[:cut].rstrip()
                print(f"物理 Q20: stem {len(stem)} -> {len(new_stem)} 字符（截断真膨胀）")
                await conn.execute(
                    "UPDATE questions SET stem = $1, status = 'approved', review_reason = NULL WHERE id = $2",
                    new_stem, q20["id"],
                )
                print("物理 Q20: 已截断 + approved")
            elif q20["stem"]:
                # 已截断过 → 直接确认 approved
                print("物理 Q20: 已无自主命制混入，确认 approved")
                await conn.execute(
                    "UPDATE questions SET status = 'approved', review_reason = NULL WHERE id = $1", q20["id"]
                )

        # ---- 化学/地理/语文 approve ----
        for subject, qn, note in APPROVE_PLAN:
            doc = await conn.fetchrow(
                "SELECT id FROM documents WHERE subject=$1 AND processing_status='completed' ORDER BY created_at DESC LIMIT 1",
                subject,
            )
            if not doc:
                print(f"{subject}: 无文档")
                continue
            row = await conn.fetchrow(
                """
                SELECT q.id, q.status, q.stem, q.answer FROM questions q
                JOIN question_instances qi ON qi.question_id = q.id
                WHERE qi.document_id = $1 AND qi.source_question_number = $2
                """,
                str(doc["id"]), qn,
            )
            if not row:
                print(f"{subject} Q{qn}: 缺库")
                continue
            if row["status"] == "approved":
                print(f"{subject} Q{qn}: 已 approved，跳过")
                continue
            if not (row["stem"] or "").strip() or not (row["answer"] or "").strip():
                print(f"{subject} Q{qn}: stem/answer 为空，跳过（{note}）")
                continue
            await conn.execute(
                "UPDATE questions SET status = 'approved', review_reason = NULL WHERE id = $1",
                row["id"],
            )
            print(f"{subject} Q{qn}: reviewing -> approved（{note}）")
    finally:
        await conn.close()


asyncio.run(main())

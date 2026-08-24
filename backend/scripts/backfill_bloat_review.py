#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""回填：膨胀误报题 reviewing → approved（BUG-022/023 数据侧）。

背景（2026-08-25）：quality_gate 新增"材料题识别"后，非综合材料分析题
（题干含材料一/二/三，如历史东城 Q43 1162 字符）不再触发膨胀检测。
本脚本扫描已完成文档的管线结果：issue 仅为"题干异常膨胀"的题，用修复后
逻辑复核存储数据（stem 非空、答案非空、按材料题上限不超长），通过则
reviewing → approved；Q41/Q42 因真实答案缺失（LLM 兜底）等其它 issue 保持
reviewing，不受影响。

用法：
    python backend/scripts/backfill_bloat_review.py [--dry-run]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncpg  # noqa: E402

from app.domains.document.quality_gate import (  # noqa: E402
    _STEM_CHAR_LIMIT_COMPOSITE,
    _STEM_CHAR_LIMIT_NON_COMPOSITE,
)

DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"


def _is_bloat_only(issues: list) -> bool:
    if not issues:
        return False
    return all("题干异常膨胀" in str(i) for i in issues)


def _recheck_inflation(stem: str, is_composite: bool, shared_ids: list) -> bool:
    """用修复后逻辑复核膨胀：返回 True 表示不再触发（通过）。"""
    has_material = bool(shared_ids) or ("材料" in (stem or ""))
    limit = _STEM_CHAR_LIMIT_COMPOSITE if (is_composite or has_material) else _STEM_CHAR_LIMIT_NON_COMPOSITE
    return len(stem or "") <= limit


async def main(dry_run: bool) -> None:
    conn = await asyncpg.connect(DSN)
    updated = 0
    skipped = []
    try:
        docs = await conn.fetch(
            """SELECT id, subject, filename FROM documents
               WHERE processing_status = 'completed'"""
        )
        for doc in docs:
            task = await conn.fetchrow(
                """SELECT result_json FROM background_tasks
                   WHERE payload_json->>'document_id' = $1
                   ORDER BY created_at DESC LIMIT 1""",
                str(doc["id"]),
            )
            if not task or not task["result_json"]:
                continue
            try:
                res = json.loads(task["result_json"])
            except Exception:
                continue
            for q in (res.get("questions") or []):
                issues = q.get("issues") or []
                if not _is_bloat_only(issues):
                    continue
                qn = str(q.get("question_number"))
                # DB 行
                row = await conn.fetchrow(
                    """SELECT q.id, q.status, q.stem, q.answer, q.is_composite,
                              q.review_reason
                       FROM questions q
                       JOIN question_instances qi ON qi.question_id = q.id
                       WHERE qi.document_id = $1 AND qi.source_question_number = $2
                       ORDER BY q.created_at DESC LIMIT 1""",
                    doc["id"], qn,
                )
                if not row or row["status"] != "reviewing":
                    continue
                if not (row["stem"] or "").strip() or not (row["answer"] or "").strip():
                    skipped.append(f"{doc['subject']} Q{qn}: stem/answer 为空，保持 reviewing")
                    continue
                if not _recheck_inflation(
                    row["stem"] or "", bool(row["is_composite"]),
                    q.get("shared_material_line_ids") or [],
                ):
                    skipped.append(f"{doc['subject']} Q{qn}: 修复后仍超长，保持 reviewing")
                    continue
                print(
                    f"{doc['subject']} Q{qn} (doc {doc['filename']}): "
                    f"reviewing({row['review_reason']}) -> approved"
                )
                if not dry_run:
                    await conn.execute(
                        "UPDATE questions SET status = 'approved', review_reason = NULL WHERE id = $1",
                        row["id"],
                    )
                updated += 1
        for s in skipped:
            print("skip:", s)
        print(f"\n{'[dry-run] ' if dry_run else ''}updated: {updated}")
    finally:
        await conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="只打印，不写库")
    args = parser.parse_args()
    asyncio.run(main(args.dry_run))

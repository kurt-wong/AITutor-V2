"""e2e 入库验收：直接查询 PostgreSQL，断言真实 PDF 入库后的数据质量。

本测试连接真实数据库（localhost:15432/aitutors），不是 mock。
用于验证 P0/P1 修复后，同一份 PDF 入库结果满足所有质量要求。

目标文档：2026北京二中高一（上）期末数学（教师版）.pdf
文档 ID：042f5b90-4a11-4c03-aabd-bd0683442dfe
修复前：question_type_id 全 NULL，difficulty 全 NULL
修复后：23 题全部有题型和难度

运行方式：
    cd backend && python -m pytest tests/test_e2e_ingestion_verification.py -v

前置条件：
    1. PostgreSQL 在 localhost:15432/aitutors 可访问
    2. 该 PDF 已通过 run_simple_pipeline 入库
"""

from __future__ import annotations

import asyncio
import pytest
from uuid import UUID

# ── 目标文档常量 ──────────────────────────────────────────────────

TARGET_DOC_ID = "042f5b90-4a11-4c03-aabd-bd0683442dfe"
TARGET_FILENAME = "2026北京二中高一（上）期末数学（教师版）.pdf"

DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"


# ── helpers ────────────────────────────────────────────────────────

async def _fetch_one(sql: str, *args):
    import asyncpg
    conn = await asyncpg.connect(DSN)
    try:
        row = await conn.fetchrow(sql, *args)
        return row
    finally:
        await conn.close()


async def _fetch_all(sql: str, *args):
    import asyncpg
    conn = await asyncpg.connect(DSN)
    try:
        rows = await conn.fetch(sql, *args)
        return rows
    finally:
        await conn.close()


def _run(coro):
    """运行 async 协程，兼容新旧 Python。"""
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


# ── 测试类 ──────────────────────────────────────────────────────────


class TestE2EIngestionVerification:
    """断言目标 PDF 入库后的数据质量（直接查 PostgreSQL）。"""

    def test_document_exists(self):
        """目标文档存在于 documents 表。"""
        row = _run(_fetch_one(
            "SELECT id, filename, processing_status FROM documents WHERE id = $1",
            TARGET_DOC_ID,
        ))
        assert row is not None, f"文档 {TARGET_DOC_ID} 不存在于 documents 表"
        assert row["processing_status"] == "completed", (
            f"文档处理状态应为 completed，实际为 {row['processing_status']}"
        )

    def test_question_count_is_23(self):
        """该文档入库题目数 = 23。"""
        row = _run(_fetch_one(
            "SELECT COUNT(*) AS cnt FROM question_instances WHERE document_id = $1",
            TARGET_DOC_ID,
        ))
        count = row["cnt"]
        assert count == 23, f"应为 23 题，实际 {count}"

    def test_question_type_distribution(self):
        """题型分布：single_choice=12, fill_in=6, short_answer=5。"""
        rows = _run(
            _fetch_all("""
                SELECT qt.code, COUNT(*) AS cnt
                FROM questions q
                JOIN question_instances qi ON qi.question_id = q.id
                LEFT JOIN question_types qt ON qt.id = q.question_type_id
                WHERE qi.document_id = $1
                GROUP BY qt.code
                ORDER BY qt.code
            """, TARGET_DOC_ID)
        )
        dist = {row["code"]: row["cnt"] for row in rows}
        assert dist == {
            "fill_in": 6,
            "short_answer": 5,
            "single_choice": 12,
        }, f"题型分布不符，实际 {dist}"

    def test_no_null_question_type(self):
        """所有题目都有题型（question_type_id IS NOT NULL）。"""
        row = _run(
            _fetch_one("""
                SELECT COUNT(*) AS cnt FROM questions q
                JOIN question_instances qi ON qi.question_id = q.id
                WHERE qi.document_id = $1
                AND q.question_type_id IS NULL
            """, TARGET_DOC_ID)
        )
        null_count = row["cnt"]
        assert null_count == 0, f"有 {null_count} 题缺少题型（question_type_id IS NULL）"

    def test_difficulty_distribution(self):
        """难度分布：1=3, 2=4, 3=10, 4=4, 5=2。"""
        rows = _run(
            _fetch_all("""
                SELECT q.difficulty, COUNT(*) AS cnt
                FROM questions q
                JOIN question_instances qi ON qi.question_id = q.id
                WHERE qi.document_id = $1
                GROUP BY q.difficulty
                ORDER BY q.difficulty
            """, TARGET_DOC_ID)
        )
        dist = {row["difficulty"]: row["cnt"] for row in rows}
        assert dist == {1: 3, 2: 4, 3: 10, 4: 4, 5: 2}, f"难度分布不符，实际 {dist}"

    def test_no_null_difficulty(self):
        """所有题目都有难度（difficulty IS NOT NULL）。"""
        row = _run(
            _fetch_one("""
                SELECT COUNT(*) AS cnt FROM questions q
                JOIN question_instances qi ON qi.question_id = q.id
                WHERE qi.document_id = $1
                AND q.difficulty IS NULL
            """, TARGET_DOC_ID)
        )
        null_count = row["cnt"]
        assert null_count == 0, f"有 {null_count} 题缺少难度（difficulty IS NULL）"

    def test_all_questions_have_stem(self):
        """所有题目都有非空题干。"""
        row = _run(
            _fetch_one("""
                SELECT COUNT(*) AS cnt FROM questions q
                JOIN question_instances qi ON qi.question_id = q.id
                WHERE qi.document_id = $1
                AND (q.stem IS NULL OR TRIM(q.stem) = '')
            """, TARGET_DOC_ID)
        )
        empty_count = row["cnt"]
        assert empty_count == 0, f"有 {empty_count} 题题干为空"

    def test_approved_status(self):
        """大部分题目应为 approved 状态（高置信度入库）。"""
        rows = _run(
            _fetch_all("""
                SELECT q.status, COUNT(*) AS cnt
                FROM questions q
                JOIN question_instances qi ON qi.question_id = q.id
                WHERE qi.document_id = $1
                GROUP BY q.status
            """, TARGET_DOC_ID)
        )
        status_map = {row["status"]: row["cnt"] for row in rows}
        assert status_map.get("approved", 0) > 0, (
            f"无 approved 题目，状态分布 {status_map}"
        )

    def test_question_type_names_not_empty(self):
        """该文档用到的题型都有中文名（name 非空）。"""
        rows = _run(
            _fetch_all("""
                SELECT DISTINCT qt.code, qt.name
                FROM questions q
                JOIN question_instances qi ON qi.question_id = q.id
                JOIN question_types qt ON qt.id = q.question_type_id
                WHERE qi.document_id = $1
            """, TARGET_DOC_ID)
        )
        for row in rows:
            code, name = row["code"], row["name"]
            assert name and name.strip(), f"题型 {code} 缺少中文名（name={name!r}）"

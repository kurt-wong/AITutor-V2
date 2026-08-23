"""
Phase 2A Step 5 真实回填 Migration Rehearsal — pytest 集成测试。

在一次性临时数据库上执行 20260821_0003 → 20260821_0005 的 upgrade，
验证 content_hash 回填：
1. 含 NULL content_hash 的历史数据被回填
2. 回填值与 Python `compute_content_hash` 结果一致（规范化规则同步）
3. 回填后无 NULL 残留
4. downgrade 将 content_hash 置空

对抗性审查修复：原 test_phase2a_step5_content_hash.py 声称覆盖回填，
但实际没有任何测试执行该 migration（总验收 SQL 在空库上是空洞通过）。
"""
import asyncio
import uuid
from pathlib import Path

import asyncpg
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"
BACKEND_DIR = Path(__file__).resolve().parent.parent
OLD_REV = "20260821_0003"   # 含 content_hash 列，无回填逻辑
NEW_REV = "20260821_0005"   # 回填 content_hash
ADMIN_DB = "postgres"
TMP_DB = "aitutors_step5_pytest"


def _parse_db_url(url: str) -> dict:
    body = url.split("://", 1)[1]
    cred, rest = body.split("@", 1)
    user, _, password = cred.partition(":")
    hostport, _, db = rest.partition("/")
    host, _, port = hostport.partition(":")
    return {"user": user, "password": password, "host": host, "port": int(port) if port else 5432, "db": db}


def _async_dsn(info: dict, db: str) -> str:
    return f"postgresql+asyncpg://{info['user']}:{info['password']}@{info['host']}:{info['port']}/{db}"


def _asyncpg_dsn(info: dict, db: str) -> str:
    return f"postgresql://{info['user']}:{info['password']}@{info['host']}:{info['port']}/{db}"


@pytest.mark.asyncio
async def test_step5_content_hash_backfill_rehearsal(monkeypatch):
    """一次性临时库执行 0005 回填 upgrade/downgrade 演练。"""
    db_info = _parse_db_url(settings.database_url)

    # ── 1. 创建临时库 ──────────────────────────────────────────
    admin_conn = await asyncpg.connect(_asyncpg_dsn(db_info, ADMIN_DB))
    try:
        exists = await admin_conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", TMP_DB)
        if exists:
            await admin_conn.execute(f'DROP DATABASE "{TMP_DB}"')
        await admin_conn.execute(f'CREATE DATABASE "{TMP_DB}"')
    finally:
        await admin_conn.close()

    monkeypatch.setattr(settings, "database_url", _async_dsn(db_info, TMP_DB))
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("prepend_sys_path", str(BACKEND_DIR))
    loop = asyncio.get_event_loop()

    try:
        # ── 2. upgrade 到 0003，插入 content_hash 为 NULL 的历史数据 ──
        await loop.run_in_executor(None, command.upgrade, cfg, OLD_REV)

        engine = create_async_engine(settings.database_url, echo=False)
        factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with factory() as session:
            subj = uuid.uuid4()
            qt_choice = uuid.uuid4()
            await session.execute(text(
                "INSERT INTO subjects (id, code, name) VALUES (:id,:c,:n)"),
                {"id": subj, "c": "step5_tst", "n": "Step5测试学科"})
            await session.execute(text(
                "INSERT INTO question_types (id, subject_id, code, name) "
                "VALUES (:id,:sid,'single_choice','单选题')"),
                {"id": qt_choice, "sid": subj})

            # 3 道历史题（content_hash 均为 NULL）
            q1, q2, q3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
            await session.execute(text(
                "INSERT INTO questions (id, subject_id, stem, options, question_type_id, "
                "source_type, status, occurrence_count) VALUES "
                "(:q1,:sid,'  已知函数  f(x)=x²  ，求值  ','[{\"label\": \"A\", \"text\": \"5\"}, "
                "{\"label\": \"B\", \"text\": \"6\"}]',:qt,'document','approved',1),"
                "(:q2,:sid,'三角函数题','[]',NULL,'document','reviewing',1),"
                "(:q3,:sid,'综合题材料',NULL,:qt,'document','reviewing',1)"),
                {"q1": q1, "q2": q2, "q3": q3, "sid": subj, "qt": qt_choice})
            await session.commit()

        # ── 3. 执行真实 migration upgrade 0005 ─────────────────
        await loop.run_in_executor(None, command.upgrade, cfg, NEW_REV)

        # ── 4. 验证回填 ───────────────────────────────────────
        from app.domains.document.content_hash import compute_content_hash

        async with engine.connect() as conn:
            rows = (await conn.execute(text(
                "SELECT id, stem, options, content_hash FROM questions ORDER BY stem"
            ))).all()
            assert len(rows) == 3
            # 无 NULL 残留（验收点 S5-5：回填后无 NULL）
            nulls = (await conn.execute(text(
                "SELECT count(*) FROM questions WHERE content_hash IS NULL"))).scalar()
            assert nulls == 0, f"回填后仍有 {nulls} 行 content_hash 为 NULL"

            # 回填值与 Python compute_content_hash 一致（规范化规则同步）
            for row in rows:
                qid, stem, options, db_hash = row
                # 从 DB 读取完整行构造期望值
                full = (await conn.execute(text(
                    "SELECT stem, options, sub_questions, qt.code AS question_type "
                    "FROM questions q LEFT JOIN question_types qt ON qt.id = q.question_type_id "
                    "WHERE q.id = :id"), {"id": qid})).one()
                expected = compute_content_hash(
                    stem=full[0],
                    options=full[1] if full[1] else None,
                    question_type=full[3],
                    sub_questions=None,
                )
                assert db_hash == expected, (
                    f"question {stem} 回填值 {db_hash} != Python 计算 {expected}（规范化规则不一致）"
                )

        # ── 5. downgrade 验证：content_hash 置空 ──────────────
        await loop.run_in_executor(None, command.downgrade, cfg, OLD_REV)

        async with engine.connect() as conn:
            n = (await conn.execute(text(
                "SELECT count(*) FROM questions WHERE content_hash IS NOT NULL"))).scalar()
            assert n == 0, "downgrade 后 content_hash 应全部置空"

        await engine.dispose()

    finally:
        admin_conn = await asyncpg.connect(_asyncpg_dsn(db_info, ADMIN_DB))
        try:
            await admin_conn.execute(f'DROP DATABASE IF EXISTS "{TMP_DB}"')
        finally:
            await admin_conn.close()

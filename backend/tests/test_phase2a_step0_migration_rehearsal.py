"""
Phase 2A Step 0 真实 Migration Rehearsal — pytest 集成测试。

在一次性临时数据库上执行完整 migration upgrade/downgrade 演练，
验证 document_id 回填、COALESCE、year/school 删除、唯一索引、downgrade 有损。

这是 Step 0 验收的核心测试（PHASE_2A_EXECUTION_PLAN.md Step 0 完成判定）。
与 scripts/step0_backfill_verify.py 等价，但以 pytest 形式纳入正式验收。

注意：需要 PostgreSQL 可达（DATABASE_URL 环境变量或 backend/.env）。
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
OLD_REV = "3d7ee1cb7c3a"
NEW_REV = "20260821_0003"
ADMIN_DB = "postgres"
TMP_DB = "aitutors_step0_pytest"


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
async def test_step0_migration_rehearsal(monkeypatch):
    """一次性临时库执行完整 migration upgrade/downgrade 演练。

    覆盖 PHASE_2A_EXECUTION_PLAN.md Step 0 全部验证项：
    1. document_id 通过 source_document_name = documents.filename 正确回填
    2. year/school COALESCE 不清空 Instance 已有值
    3. questions.year/school 被删除
    4. 唯一索引拒绝重复 (document_id, source_question_number)
    5. migration downgrade 能回退 schema（有损，数据不恢复）

    用 monkeypatch 替代手动 settings 赋值，保证即使测试崩溃也能恢复原始值。
    """
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

    # monkeypatch 保证 settings.database_url 在测试结束（含异常）时恢复
    monkeypatch.setattr(settings, "database_url", _async_dsn(db_info, TMP_DB))
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("prepend_sys_path", str(BACKEND_DIR))
    loop = asyncio.get_event_loop()

    try:
        # ── 2. upgrade 到旧 head，插入旧 schema 数据 ──────────
        await loop.run_in_executor(None, command.upgrade, cfg, OLD_REV)

        engine = create_async_engine(settings.database_url, echo=False)
        factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with factory() as session:
            subj = uuid.uuid4()
            await session.execute(text(
                "INSERT INTO subjects (id, code, name) VALUES (:id,:c,:n)"),
                {"id": subj, "c": "step0_tst", "n": "Step0测试学科"})

            doc1, doc2 = uuid.uuid4(), uuid.uuid4()
            await session.execute(text(
                "INSERT INTO documents (id, filename, file_type, object_key) "
                "VALUES (:d1,'paper_a.pdf','pdf','test/a'),(:d2,'paper_b.pdf','pdf','test/b')"),
                {"d1": doc1, "d2": doc2})

            q1, q2, q3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
            await session.execute(text(
                "INSERT INTO questions (id, subject_id, stem, source_type, source_document_name, "
                "status, occurrence_count, year, school) VALUES "
                "(:q1,:sid,'Q1 题干','document','paper_a.pdf','reviewing',1,2024,'朝阳中学'),"
                "(:q2,:sid,'Q2 题干','document','paper_a.pdf','reviewing',1,NULL,'海淀中学'),"
                "(:q3,:sid,'Q3 题干','document','paper_b.pdf','reviewing',1,2025,NULL)"),
                {"q1": q1, "q2": q2, "q3": q3, "sid": subj})

            i1, i2, i3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
            # 旧 schema question_instances 无 document_id 列
            await session.execute(text(
                "INSERT INTO question_instances (id, question_id, source_type, source_document_name, "
                "source_question_number, year, school, occurrence_no) VALUES "
                "(:i1,:q1,'document','paper_a.pdf','1',NULL,NULL,1),"
                "(:i2,:q2,'document','paper_a.pdf','2',2030,'已有学校',1),"
                "(:i3,:q3,'document','paper_b.pdf','3',NULL,NULL,1)"),
                {"i1": i1, "i2": i2, "i3": i3, "q1": q1, "q2": q2, "q3": q3})
            await session.commit()

        # ── 3. 执行真实 migration upgrade ──────────────────────
        await loop.run_in_executor(None, command.upgrade, cfg, NEW_REV)

        # ── 4. 验证回填 ───────────────────────────────────────
        async with engine.connect() as conn:
            # 4a. questions.year/school 已删除
            qcols = (await conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='questions' AND column_name IN ('year','school')"))).all()
            assert len(qcols) == 0, f"残留列: {[r[0] for r in qcols]}"

            # 4b. document_id 回填（source_document_name = filename）
            rows = (await conn.execute(text("""
                SELECT qi.source_question_number, (qi.document_id = d.id) AS matched
                FROM question_instances qi
                JOIN documents d ON d.filename = qi.source_document_name
                WHERE qi.source_type='document' ORDER BY qi.source_question_number
            """))).all()
            assert len(rows) == 3
            for r in rows:
                assert r[1] is True, f"Q{r[0]} document_id 未匹配"

            # 4c. COALESCE 不清空已有值
            rows = (await conn.execute(text(
                "SELECT source_question_number, year, school FROM question_instances "
                "WHERE source_type='document' ORDER BY source_question_number"))).all()
            by_qno = {r[0]: (r[1], r[2]) for r in rows}
            assert by_qno["1"] == (2024, "朝阳中学"), "Q1 回填失败"
            assert by_qno["2"] == (2030, "已有学校"), "Q2 COALESCE 未保留已有值"
            assert by_qno["3"] == (2025, None), "Q3 COALESCE 失败"

            # 4d. document_id NULL 计数 = 0
            n = (await conn.execute(text(
                "SELECT count(*) FROM question_instances "
                "WHERE source_type='document' AND document_id IS NULL"))).scalar()
            assert n == 0

            # 4e. 唯一索引存在
            idx = (await conn.execute(text(
                "SELECT indexname FROM pg_indexes "
                "WHERE tablename='question_instances' "
                "AND indexname='ix_question_instances_doc_qno'"))).all()
            assert len(idx) == 1

            # 4f. 无重复 (document_id, source_question_number)
            dup = (await conn.execute(text("""
                SELECT count(*) FROM (
                    SELECT document_id, source_question_number
                    FROM question_instances
                    WHERE source_type='document' AND source_question_number IS NOT NULL
                    GROUP BY document_id, source_question_number HAVING count(*) > 1
                ) t
            """))).scalar()
            assert dup == 0

            # 4g. 唯一索引负面用例：重复插入被拒绝
            with pytest.raises(Exception, match="duplicate key"):
                await conn.execute(text("""
                    INSERT INTO question_instances
                        (id, question_id, document_id, source_type, source_document_name,
                         source_question_number, occurrence_no)
                    VALUES (:id, :qid, :doc, 'document', 'paper_a.pdf', '1', 2)
                """), {"id": uuid.uuid4(), "qid": q1, "doc": doc1})

        # ── 5. downgrade 验证（有损） ─────────────────────────
        await loop.run_in_executor(None, command.downgrade, cfg, OLD_REV)

        async with engine.connect() as conn:
            # year/school 恢复
            qcols = (await conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='questions' AND column_name IN ('year','school') "
                "ORDER BY column_name"))).all()
            assert set(r[0] for r in qcols) == {"year", "school"}, "year/school 未恢复"

            # document_id 移除
            icols = (await conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='question_instances' AND column_name='document_id'"))).all()
            assert len(icols) == 0, "document_id 未移除"

            # instance 行保留（有损：document_id 数据不恢复）
            n = (await conn.execute(text(
                "SELECT count(*) FROM question_instances "
                "WHERE source_type='document'"))).scalar()
            assert n == 3

        await engine.dispose()

    finally:
        # monkeypatch 自动恢复 settings.database_url，只需清理临时库
        admin_conn = await asyncpg.connect(_asyncpg_dsn(db_info, ADMIN_DB))
        try:
            await admin_conn.execute(f'DROP DATABASE IF EXISTS "{TMP_DB}"')
        finally:
            await admin_conn.close()

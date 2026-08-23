"""Phase 2A Step 0 真实回填演练脚本。

在一次性临时数据库中构造旧 schema 数据，实际执行 migration upgrade，验证：
1. document_id 通过 source_document_name = documents.filename 正确回填
2. year/school 使用 COALESCE，不清空 Instance 已有值
3. questions.year/school 被删除
4. 唯一索引拒绝重复 (document_id, source_question_number)（upgrade 后插入负面用例）
5. migration downgrade 能回退 schema（有损，数据不恢复）

用法（backend 目录，backend/.env 的 DATABASE_URL 指向主库 aitutors，脚本自动创建临时库）：
    python -m scripts.step0_backfill_verify
"""
import asyncio
import sys
import uuid

import asyncpg
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

sys.stdout.reconfigure(encoding="utf-8")

# 目标 revision（旧 head = 20260821_0003 之前；新 head = 20260821_0003）
OLD_REV = "3d7ee1cb7c3a"
NEW_REV = "20260821_0003"

ADMIN_DB = "postgres"          # 管理员库（建库用）
TMP_DB = "aitutors_step0_verify"


def _parse_db_url(url: str) -> dict:
    """解析 postgresql+asyncpg://user:pass@host:port/db 连接信息。"""
    body = url.split("://", 1)[1]
    cred, rest = body.split("@", 1)
    user, _, password = cred.partition(":")
    hostport, _, db = rest.partition("/")
    host, _, port = hostport.partition(":")
    return {
        "user": user,
        "password": password,
        "host": host,
        "port": int(port) if port else 5432,
        "db": db,
    }


def _async_dsn(info: dict, db: str) -> str:
    """构造 async 驱动 DSN（create_async_engine 用）。"""
    return (
        f"postgresql+asyncpg://{info['user']}:{info['password']}"
        f"@{info['host']}:{info['port']}/{db}"
    )


def _asyncpg_dsn(info: dict, db: str) -> str:
    """构造 asyncpg 原生 DSN（asyncpg.connect 用，不带 +asyncpg 后缀）。"""
    return (
        f"postgresql://{info['user']}:{info['password']}"
        f"@{info['host']}:{info['port']}/{db}"
    )


async def _create_tmp_db(info: dict) -> None:
    conn = await asyncpg.connect(_asyncpg_dsn(info, ADMIN_DB))
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", TMP_DB
        )
        if exists:
            await conn.execute(f'DROP DATABASE "{TMP_DB}"')
        await conn.execute(f'CREATE DATABASE "{TMP_DB}"')
    finally:
        await conn.close()
    print(f"[create] 临时库 {TMP_DB} 已创建")


async def _drop_tmp_db(info: dict) -> None:
    conn = await asyncpg.connect(_asyncpg_dsn(info, ADMIN_DB))
    try:
        await conn.execute(f'DROP DATABASE IF EXISTS "{TMP_DB}"')
    finally:
        await conn.close()
    print(f"[cleanup] 临时库 {TMP_DB} 已删除")


def _alembic() -> Config:
    return Config("alembic.ini")


async def _migrate(rev: str) -> None:
    """执行 alembic upgrade 到指定 revision（settings.database_url 已指向临时库）。"""
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, command.upgrade, _alembic(), rev)
    print(f"[alembic] upgrade -> {rev} 完成")


async def _downgrade(rev: str) -> None:
    """执行 alembic downgrade 到指定 revision。"""
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, command.downgrade, _alembic(), rev)
    print(f"[alembic] downgrade -> {rev} 完成")


async def _seed_old_schema() -> dict:
    """在旧 schema（OLD_REV）上插入旧结构数据。

    数据设计（覆盖执行计划 Step 0 要求）：
    - 2 个 document，filename 与 Instance.source_document_name 匹配
    - 3 个 question，覆盖 year/school 缺失边界：
      q1: year=2024, school='朝阳中学'（Instance 两者皆 NULL → 全部回填）
      q2: year=NULL,  school='海淀中学'（Instance.school 已有值 → COALESCE 保留）
      q3: year=2025,  school=NULL    （Instance.year 已有值 → COALESCE 保留）
    - 主流程不含重复行（重复负面用例在 upgrade 后单独验证，避免 migration 失败中断验证）
    """
    engine = create_async_engine(_async_dsn(_DB_INFO, TMP_DB), echo=False)
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    ids: dict[str, str] = {}
    try:
        async with factory() as session:
            subj = uuid.uuid4()
            await session.execute(
                text("INSERT INTO subjects (id, code, name) VALUES (:id, :code, :name)"),
                {"id": subj, "code": "step0_verify", "name": "Step0验证学科"},
            )
            ids["subject_id"] = str(subj)

            doc1 = uuid.uuid4()
            doc2 = uuid.uuid4()
            await session.execute(
                text("""
                    INSERT INTO documents (id, filename, file_type, object_key)
                    VALUES (:d1, 'paper_a.pdf', 'pdf', 'test/paper_a.pdf'),
                           (:d2, 'paper_b.pdf', 'pdf', 'test/paper_b.pdf')
                """),
                {"d1": doc1, "d2": doc2},
            )
            ids["doc1"] = str(doc1)
            ids["doc2"] = str(doc2)

            q1 = uuid.uuid4()
            q2 = uuid.uuid4()
            q3 = uuid.uuid4()
            await session.execute(
                text("""
                    INSERT INTO questions (id, subject_id, stem, source_type, source_document_name,
                                           status, occurrence_count, year, school)
                    VALUES (:q1, :sid, 'Q1 题干', 'document', 'paper_a.pdf', 'reviewing', 1, 2024, '朝阳中学'),
                           (:q2, :sid, 'Q2 题干', 'document', 'paper_a.pdf', 'reviewing', 1, NULL, '海淀中学'),
                           (:q3, :sid, 'Q3 题干', 'document', 'paper_b.pdf', 'reviewing', 1, 2025, NULL)
                """),
                {"q1": q1, "q2": q2, "q3": q3, "sid": subj},
            )
            ids["q1"] = str(q1)
            ids["q2"] = str(q2)
            ids["q3"] = str(q3)

            # 旧 schema 的 question_instances 没有 document_id 列（只有 source_document_name）
            i1 = uuid.uuid4()
            i2 = uuid.uuid4()
            i3 = uuid.uuid4()
            await session.execute(
                text("""
                    INSERT INTO question_instances (id, question_id, source_type, source_document_name,
                                                    source_question_number, year, school, occurrence_no)
                    VALUES (:i1, :q1, 'document', 'paper_a.pdf', '1', NULL, NULL, 1),
                           (:i2, :q2, 'document', 'paper_a.pdf', '2', 2030, '已有学校', 1),
                           (:i3, :q3, 'document', 'paper_b.pdf', '3', NULL, NULL, 1)
                """),
                {"i1": i1, "i2": i2, "i3": i3, "q1": q1, "q2": q2, "q3": q3},
            )
            ids["i1"] = str(i1)
            ids["i2"] = str(i2)
            ids["i3"] = str(i3)
            await session.commit()
    finally:
        await engine.dispose()
    print("[seed] 旧 schema 数据已插入：2 documents / 3 questions / 3 instances")
    return ids


async def _verify_backfill(ids: dict) -> None:
    """upgrade 到新 head 后执行验证 SQL。"""
    engine = create_async_engine(_async_dsn(_DB_INFO, TMP_DB), echo=False)
    try:
        async with engine.connect() as conn:
            print("\n=== 1. questions.year/school 已删除（列不存在） ===")
            cols = (await conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='questions' AND column_name IN ('year','school')"
            ))).all()
            print(f"残留列数 = {len(cols)}（期望 0）")

            print("\n=== 2. document_id 回填（source_document_name = filename） ===")
            rows = (await conn.execute(text("""
                SELECT qi.source_question_number, d.filename,
                       (qi.document_id = d.id) AS doc_matched
                FROM question_instances qi
                JOIN documents d ON d.filename = qi.source_document_name
                WHERE qi.source_type='document'
                ORDER BY qi.source_question_number
            """))).all()
            for r in rows:
                print(f"  Q{r[0]} -> document='{r[1]}' doc_id匹配={r[2]}")

            print("\n=== 3. year/school COALESCE 回填（不清空已有值） ===")
            rows = (await conn.execute(text("""
                SELECT source_question_number, year, school FROM question_instances
                WHERE source_type='document' ORDER BY source_question_number
            """))).all()
            for r in rows:
                print(f"  Q{r[0]}: year={r[1]}, school={r[2]}")

            print("\n=== 4. NULL document_id 计数（期望 0） ===")
            n = (await conn.execute(text(
                "SELECT count(*) FROM question_instances WHERE source_type='document' AND document_id IS NULL"
            ))).scalar()
            print(f"  count = {n}")

            print("\n=== 5. 唯一索引存在性 ===")
            idx = (await conn.execute(text(
                "SELECT indexname FROM pg_indexes WHERE tablename='question_instances' "
                "AND indexname='ix_question_instances_doc_qno'"
            ))).all()
            print(f"  ix_question_instances_doc_qno = {'存在' if idx else '缺失'}")

            print("\n=== 6. 重复 (document_id, source_question_number) 计数（回填后） ===")
            dup = (await conn.execute(text("""
                SELECT count(*) FROM (
                    SELECT document_id, source_question_number
                    FROM question_instances
                    WHERE source_type='document' AND source_question_number IS NOT NULL
                    GROUP BY document_id, source_question_number HAVING count(*) > 1
                ) t
            """))).scalar()
            print(f"  重复组数 = {dup}（期望 0）")
    finally:
        await engine.dispose()


async def _verify_unique_index_rejects(ids: dict) -> None:
    """验证唯一索引真实拒绝重复插入（负面用例在 upgrade 后执行）。"""
    engine = create_async_engine(_async_dsn(_DB_INFO, TMP_DB), echo=False)
    try:
        async with engine.connect() as conn:
            print("\n=== 7. 唯一索引负面用例：重复插入被拒绝 ===")
            try:
                await conn.execute(text("""
                    INSERT INTO question_instances
                        (id, question_id, document_id, source_type, source_document_name,
                         source_question_number, occurrence_no)
                    VALUES (:id, :qid, :doc, 'document', 'paper_a.pdf', '1', 2)
                """), {
                    "id": uuid.uuid4(), "qid": ids["q1"], "doc": ids["doc1"],
                })
                print("  意外：重复插入成功（应被拒绝）")
            except Exception as exc:
                print(f"  正确拒绝：{type(exc).__name__}: {str(exc)[:140]}")
    finally:
        await engine.dispose()


async def _verify_downgrade() -> None:
    """downgrade 到旧 head 后验证 schema 回退（有损）。"""
    engine = create_async_engine(_async_dsn(_DB_INFO, TMP_DB), echo=False)
    try:
        async with engine.connect() as conn:
            print("\n=== 8. downgrade 后 schema 验证 ===")
            qcols = (await conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='questions' AND column_name IN ('year','school') ORDER BY column_name"
            ))).all()
            print(f"  questions.year/school 列恢复 = {[c[0] for c in qcols]}")
            icols = (await conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='question_instances' AND column_name='document_id'"
            ))).all()
            print(f"  question_instances.document_id 列存在 = {bool(icols)}（期望 False，已移除）")
            n = (await conn.execute(text(
                "SELECT count(*) FROM question_instances WHERE source_type='document'"
            ))).scalar()
            print(f"  剩余 instance 行数 = {n}（downgrade 有损：回填的 document_id 数据不恢复，行保留）")
    finally:
        await engine.dispose()


async def main() -> None:
    global _DB_INFO
    from app.core.config import settings

    _DB_INFO = _parse_db_url(settings.database_url)
    print(f"主库: {_DB_INFO['host']}:{_DB_INFO['port']}/{_DB_INFO['db']}")
    print(f"临时库: {TMP_DB}（一次性，演练后删除）")

    await _create_tmp_db(_DB_INFO)
    try:
        # 关键：alembic env.py 从 settings.database_url 取连接串，必须指向临时库
        settings.database_url = _async_dsn(_DB_INFO, TMP_DB)

        # 1. 旧 schema 就绪（upgrade 到 OLD_REV）
        await _migrate(OLD_REV)
        # 2. 插入旧结构数据
        ids = await _seed_old_schema()
        # 3. 实际执行 migration upgrade 到新 head（含 document_id/year/school 回填）
        await _migrate(NEW_REV)
        # 4. 验证回填
        await _verify_backfill(ids)
        # 5. 唯一索引负面用例（upgrade 后插入重复行应被拒绝）
        await _verify_unique_index_rejects(ids)
        # 6. downgrade 回退验证（用 command.downgrade，upgrade 到祖先 revision 是 no-op）
        await _downgrade(OLD_REV)
        await _verify_downgrade()
        print("\n=== Step 0 真实回填演练完成 ===")
    finally:
        await _drop_tmp_db(_DB_INFO)


if __name__ == "__main__":
    asyncio.run(main())

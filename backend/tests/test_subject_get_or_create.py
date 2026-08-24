"""2026-08-25 测试：_get_or_create_subject 加固（垃圾 subject 行防护）。

历史脏行根因：LLM 答案提取返回空/非规范 subject（''、英语(A班)、高一物理、
生物学），_get_or_create_subject 查不到就创建 → subjects 表出现空名与垃圾行，
28 题指向空名 subject，且知识点被回退映射到 MATH-UNKNOWN。

加固后行为：
- 空名/纯空白 → 回退"未知"（不创建空名行）
- 非规范别名 → 归一化到 canonical（生物学→生物、英语(A班)→英语、高一物理→物理）
- 未知名称 → 告警并回退"未知"，不创建垃圾行
"""

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.domains.document.ingestion import _get_or_create_subject
from app.models import Subject


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.connect() as conn:
        async with conn.begin() as transaction:
            session = AsyncSession(bind=conn, expire_on_commit=False)
            yield session
            await transaction.rollback()
    await engine.dispose()


async def _count_by_name(db, name: str) -> int:
    return int(await db.scalar(
        select(func.count()).select_from(Subject).where(Subject.name == name)
    ) or 0)


class TestGetOrCreateSubjectHardening:
    @pytest.mark.asyncio
    async def test_empty_name_falls_back_to_unknown(self, db):
        """空名/纯空白不创建空名行，回退"未知"。"""
        subj = await _get_or_create_subject(db, "   ")
        assert subj.name == "未知"
        assert await _count_by_name(db, "") == 0

    @pytest.mark.asyncio
    async def test_alias_normalized_to_canonical(self, db):
        """非规范别名归一化到 canonical 科目，不创建别名垃圾行。"""
        subj = await _get_or_create_subject(db, "生物学")
        assert subj.name == "生物"
        assert await _count_by_name(db, "生物学") == 0

        subj2 = await _get_or_create_subject(db, "英语(A班)")
        assert subj2.name == "英语"
        assert await _count_by_name(db, "英语(A班)") == 0

        subj3 = await _get_or_create_subject(db, "高一物理")
        assert subj3.name == "物理"
        assert await _count_by_name(db, "高一物理") == 0

    @pytest.mark.asyncio
    async def test_unknown_name_falls_back_to_unknown(self, db):
        """未知名称（LLM 幻觉/班级名）不创建垃圾行，回退"未知"。"""
        junk = "高一(3)班数学提高"
        before = await _count_by_name(db, junk)
        subj = await _get_or_create_subject(db, junk)
        assert subj.name == "未知"
        assert await _count_by_name(db, junk) == before

    @pytest.mark.asyncio
    async def test_canonical_creates_and_reuses(self, db):
        """canonical 名称正常 get-or-create 且不重复。"""
        subj = await _get_or_create_subject(db, "历史")
        assert subj.name == "历史"
        subj2 = await _get_or_create_subject(db, "历史")
        assert subj2.id == subj.id
        assert await _count_by_name(db, "历史") == 1

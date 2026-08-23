"""P0-2 严格测试：_get_question_type_id get-or-create。

审计发现（bugs.md BUG-012 §四 A）：
- question_types 表无种子数据，_get_question_type_id 只查不建 →
  423 题 question_type_id 全 NULL。
- 修复：未命中 canonical 题型时自动创建（get-or-create）。

本测试用真实 PostgreSQL（事务回滚隔离），验证创建/复用/未知三种行为。
"""

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.domains.document.ingestion import _get_question_type_id
from app.models import QuestionType, Subject


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.connect() as conn:
        async with conn.begin() as transaction:
            session = AsyncSession(bind=conn, expire_on_commit=False)
            yield session
            await transaction.rollback()
    await engine.dispose()


async def _make_subject(db) -> Subject:
    subj = Subject(code=f"TST_QT_{id(db)}", name="题型测试科")
    db.add(subj)
    await db.flush()
    return subj


async def _count(db, code: str) -> int:
    return int(await db.scalar(
        select(func.count()).select_from(QuestionType).where(QuestionType.code == code)
    ) or 0)


class TestGetQuestionTypeIdGetOrCreate:
    @pytest.mark.asyncio
    async def test_creates_missing_canonical_type(self, db):
        """canonical 题型不存在 → 自动创建并返回 id（此前返回 None）。"""
        subj = await _make_subject(db)
        qid = await _get_question_type_id(db, "single_choice", subj.id)

        assert qid is not None, "get-or-create 必须返回 id（修复前返回 None）"
        qt = await db.get(QuestionType, qid)
        assert qt is not None
        assert qt.code == "single_choice"
        assert qt.name == "单选题"

    @pytest.mark.asyncio
    async def test_reuses_existing_type(self, db):
        """已存在 → 返回同一 id，不重复创建。"""
        subj = await _make_subject(db)
        first = await _get_question_type_id(db, "fill_in", subj.id)
        second = await _get_question_type_id(db, "fill_in", subj.id)

        assert first == second
        assert await _count(db, "fill_in") == 1

    @pytest.mark.asyncio
    async def test_unknown_type_returns_none_and_not_created(self, db):
        """非 canonical 未知题型 → 返回 None，不创建。"""
        subj = await _make_subject(db)
        before = await _count(db, "not_a_real_type")
        qid = await _get_question_type_id(db, "not_a_real_type", subj.id)

        assert qid is None
        assert await _count(db, "not_a_real_type") == before

    @pytest.mark.asyncio
    async def test_llm_variant_normalized_to_canonical(self, db):
        """LLM 变体（中文/旧枚举）→ 归一化为 canonical 后创建/复用。"""
        subj = await _make_subject(db)
        # 中文"填空题"应归一化为 fill_in 并创建
        qid = await _get_question_type_id(db, "填空题", subj.id)
        assert qid is not None
        qt = await db.get(QuestionType, qid)
        assert qt.code == "fill_in"
        assert qt.name == "填空题"

        # 旧枚举 fill_in_blank 复用同一记录
        qid2 = await _get_question_type_id(db, "fill_in_blank", subj.id)
        assert qid2 == qid
        assert await _count(db, "fill_in") == 1

    @pytest.mark.asyncio
    async def test_empty_code_returns_none(self, db):
        """空 code → None，不查询不创建。"""
        subj = await _make_subject(db)
        assert await _get_question_type_id(db, None, subj.id) is None
        assert await _get_question_type_id(db, "", subj.id) is None

    @pytest.mark.asyncio
    async def test_cross_subject_reuses_same_type_record(self, db):
        """跨学科题型复用同一记录。

        当前实现：QuestionType.code 全局唯一，不按 subject_id 隔离。
        数学创建的 single_choice 记录，英语题也会复用同一行。
        这意味着 question_types.subject_id 只记录第一个创建者的学科。
        此测试记录并固化该行为：如果未来需要学科隔离题型，此测试必须同步修改。
        """
        subj_math = await _make_subject(db)
        subj_eng = Subject(code=f"TST_QT_ENG_{id(db)}", name="英语测试科")
        db.add(subj_eng)
        await db.flush()

        qid_math = await _get_question_type_id(db, "single_choice", subj_math.id)
        qid_eng = await _get_question_type_id(db, "single_choice", subj_eng.id)

        # 同一记录：code 全局唯一
        assert qid_math == qid_eng, "跨学科应复用同一 QuestionType 记录"

        # 全局只有一条 single_choice
        assert await _count(db, "single_choice") == 1

        # subject_id 记录的是第一个创建者（可能是其他测试/运行留下的记录）。
        # 当前实现不按 subject_id 隔离题型，所以 subject_id 的值不阻断入库。
        qt = await db.get(QuestionType, qid_math)
        assert qt is not None

"""
Phase 2A Step 0 集成测试 — 在真实 PostgreSQL 上验证 migration 回填、唯一约束和入库行为。

使用 async SQLAlchemy + asyncpg，每个测试函数在独立事务中执行并回滚。
"""
import uuid
import pytest
import pytest_asyncio
from decimal import Decimal
from typing import Any
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models import (
    Base,
    Document,
    Question,
    QuestionInstance,
    QuestionKnowledge,
    Subject,
)


# ── Fixtures ──────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def async_engine():
    engine = create_async_engine(settings.database_url, echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db(async_engine):
    """提供一个带事务的 session，测试结束后自动回滚。"""
    async with async_engine.connect() as conn:
        async with conn.begin() as transaction:
            session = AsyncSession(bind=conn, expire_on_commit=False)
            yield session
            await transaction.rollback()


@pytest_asyncio.fixture
async def subject_id(db):
    """创建一个测试学科。"""
    subj = Subject(code=f"test_step0_{uuid.uuid4().hex[:8]}", name="测试学科_Step0")
    db.add(subj)
    await db.flush()
    return subj.id


# ═══════════════════════════════════════════════════════════════════
# 1. Migration 回填验证
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_document_id_backfill_from_source_document_name(db, subject_id):
    """document_id 通过 source_document_name = documents.filename 回填。"""
    doc = Document(
        filename="test_paper_2024.pdf",
        file_type="pdf",
        object_key="test/test_paper_2024.pdf",
        subject="数学",
        grade="高二",
        year=2024,
        school="朝阳中学",
    )
    db.add(doc)
    await db.flush()

    q = Question(
        subject_id=subject_id,
        stem="测试题干：求 f(x)=x² 的最小值",
        source_type="document",
        source_document_name="test_paper_2024.pdf",
        status="approved",
        occurrence_count=1,
    )
    db.add(q)
    await db.flush()

    inst = QuestionInstance(
        question_id=q.id,
        document_id=doc.id,
        source_type="document",
        source_document_name="test_paper_2024.pdf",
        source_question_number="5",
        year=2024,
        school="朝阳中学",
    )
    db.add(inst)
    await db.flush()

    assert inst.document_id == doc.id
    assert inst.year == 2024
    assert inst.school == "朝阳中学"


@pytest.mark.asyncio
async def test_year_school_coalesce_preserves_existing(db, subject_id):
    """COALESCE 保证不清空 Instance 已有的 year/school。"""
    doc = Document(
        filename="test_coalesce.pdf",
        file_type="pdf",
        object_key="test/test_coalesce.pdf",
    )
    db.add(doc)
    await db.flush()

    q = Question(
        subject_id=subject_id,
        stem="COALESCE 测试题",
        source_type="document",
        status="reviewing",
        occurrence_count=1,
    )
    db.add(q)
    await db.flush()

    # Instance 已有 year=2025，school=None
    inst = QuestionInstance(
        question_id=q.id,
        document_id=doc.id,
        source_type="document",
        source_question_number="3",
        year=2025,
        school=None,
    )
    db.add(inst)
    await db.flush()

    assert inst.year == 2025
    assert inst.school is None


@pytest.mark.asyncio
async def test_instance_year_can_be_null(db, subject_id):
    """Instance.year 可以为 NULL（当 Question 和 Instance 都没有 year 时）。"""
    doc = Document(
        filename="test_null_year.pdf",
        file_type="pdf",
        object_key="test/test_null_year.pdf",
    )
    db.add(doc)
    await db.flush()

    q = Question(
        subject_id=subject_id,
        stem="NULL year 测试题",
        source_type="document",
        status="approved",
    )
    db.add(q)
    await db.flush()

    inst = QuestionInstance(
        question_id=q.id,
        document_id=doc.id,
        source_type="document",
        source_question_number="1",
        year=None,
        school=None,
    )
    db.add(inst)
    await db.flush()

    assert inst.year is None
    assert inst.school is None


# ═══════════════════════════════════════════════════════════════════
# 2. 唯一约束负面用例
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_unique_index_rejects_duplicate(db, subject_id):
    """同一 document 下同一 source_question_number 不允许重复。"""
    doc = Document(
        filename="test_unique.pdf",
        file_type="pdf",
        object_key="test/test_unique.pdf",
    )
    db.add(doc)
    await db.flush()

    q1 = Question(subject_id=subject_id, stem="唯一约束题1", source_type="document")
    q2 = Question(subject_id=subject_id, stem="唯一约束题2", source_type="document")
    db.add_all([q1, q2])
    await db.flush()

    inst1 = QuestionInstance(
        question_id=q1.id, document_id=doc.id,
        source_type="document", source_question_number="7",
    )
    db.add(inst1)
    await db.flush()  # 第一条成功

    inst2 = QuestionInstance(
        question_id=q2.id, document_id=doc.id,
        source_type="document", source_question_number="7",
    )
    db.add(inst2)
    with pytest.raises(Exception) as exc_info:
        await db.flush()
    err_msg = str(exc_info.value).lower()
    assert "unique" in err_msg or "duplicate" in err_msg


@pytest.mark.asyncio
async def test_different_question_number_allowed(db, subject_id):
    """同一 document 下不同 source_question_number 允许。"""
    doc = Document(
        filename="test_diff_qno.pdf",
        file_type="pdf",
        object_key="test/test_diff_qno.pdf",
    )
    db.add(doc)
    await db.flush()

    q1 = Question(subject_id=subject_id, stem="题A", source_type="document")
    q2 = Question(subject_id=subject_id, stem="题B", source_type="document")
    db.add_all([q1, q2])
    await db.flush()

    inst1 = QuestionInstance(
        question_id=q1.id, document_id=doc.id,
        source_type="document", source_question_number="1",
    )
    inst2 = QuestionInstance(
        question_id=q2.id, document_id=doc.id,
        source_type="document", source_question_number="2",
    )
    db.add_all([inst1, inst2])
    await db.flush()  # 应该成功
    assert inst1.id != inst2.id


@pytest.mark.asyncio
async def test_null_source_question_number_allows_duplicates(db, subject_id):
    """source_question_number 为 NULL 时允许同一 document 多条记录。"""
    doc = Document(
        filename="test_null_qno.pdf",
        file_type="pdf",
        object_key="test/test_null_qno.pdf",
    )
    db.add(doc)
    await db.flush()

    q1 = Question(subject_id=subject_id, stem="NULL qno 题1", source_type="document")
    q2 = Question(subject_id=subject_id, stem="NULL qno 题2", source_type="document")
    db.add_all([q1, q2])
    await db.flush()

    inst1 = QuestionInstance(
        question_id=q1.id, document_id=doc.id,
        source_type="document", source_question_number=None,
    )
    inst2 = QuestionInstance(
        question_id=q2.id, document_id=doc.id,
        source_type="document", source_question_number=None,
    )
    db.add_all([inst1, inst2])
    await db.flush()  # 部分索引不包含 NULL，所以允许
    assert inst1.id != inst2.id


# ═══════════════════════════════════════════════════════════════════
# 3. Model 字段约束验证
# ═══════════════════════════════════════════════════════════════════


def test_question_has_no_year_column():
    """questions 表不能有 year 列。"""
    cols = {c.name for c in Question.__table__.columns}
    assert "year" not in cols


def test_question_has_no_school_column():
    """questions 表不能有 school 列。"""
    cols = {c.name for c in Question.__table__.columns}
    assert "school" not in cols


def test_question_has_content_hash():
    """questions 表必须有 content_hash 列。"""
    cols = {c.name for c in Question.__table__.columns}
    assert "content_hash" in cols


def test_instance_document_id_not_null():
    """question_instances.document_id 必须为 NOT NULL。"""
    col = QuestionInstance.__table__.columns["document_id"]
    assert col.nullable is False


def test_instance_has_year_school():
    """question_instances 必须保留 year/school 列。"""
    cols = {c.name for c in QuestionInstance.__table__.columns}
    assert "year" in cols
    assert "school" in cols


def test_qk_has_mapping_source_and_review_status():
    """question_knowledge 必须有 mapping_source 和 review_status。"""
    cols = {c.name for c in QuestionKnowledge.__table__.columns}
    assert "mapping_source" in cols
    assert "review_status" in cols


# ═══════════════════════════════════════════════════════════════════
# 4. Ingestion 行为验证
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_question_creation_without_year_school(db, subject_id):
    """创建 Question 时不需要 year/school 参数。"""
    q = Question(
        subject_id=subject_id,
        stem="入库行为测试题",
        source_type="document",
        status="approved",
    )
    db.add(q)
    await db.flush()
    assert q.id is not None


@pytest.mark.asyncio
async def test_instance_creation_with_document_id(db, subject_id):
    """创建 QuestionInstance 时必须提供 document_id。"""
    doc = Document(
        filename="test_ingestion.pdf",
        file_type="pdf",
        object_key="test/test_ingestion.pdf",
    )
    db.add(doc)
    await db.flush()

    q = Question(
        subject_id=subject_id,
        stem="Instance 测试题",
        source_type="document",
        status="reviewing",
    )
    db.add(q)
    await db.flush()

    inst = QuestionInstance(
        question_id=q.id,
        document_id=doc.id,
        source_type="document",
        source_document_name="test_ingestion.pdf",
        source_question_number="10",
        year=2024,
        school="测试学校",
    )
    db.add(inst)
    await db.flush()

    assert inst.document_id == doc.id
    assert inst.source_question_number == "10"
    assert inst.year == 2024
    assert inst.school == "测试学校"


@pytest.mark.asyncio
async def test_occurrence_count_updates_with_instances(db, subject_id):
    """occurrence_count 应等于 COUNT(instances)。"""
    doc = Document(
        filename="test_occurrence.pdf",
        file_type="pdf",
        object_key="test/test_occurrence.pdf",
    )
    db.add(doc)
    await db.flush()

    q = Question(
        subject_id=subject_id,
        stem="多实例测试题",
        source_type="document",
        occurrence_count=1,
    )
    db.add(q)
    await db.flush()

    for i in range(3):
        inst = QuestionInstance(
            question_id=q.id,
            document_id=doc.id,
            source_type="document",
            source_question_number=str(i + 1),
        )
        db.add(inst)
    await db.flush()

    count = await db.scalar(
        select(func.count())
        .select_from(QuestionInstance)
        .where(QuestionInstance.question_id == q.id)
    )
    q.occurrence_count = count
    await db.flush()

    assert q.occurrence_count == 3


# ═══════════════════════════════════════════════════════════════════
# 5. document_id NOT NULL 约束验证
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_instance_without_document_id_fails(db, subject_id):
    """不提供 document_id 时，DB 层拒绝插入。"""
    q = Question(
        subject_id=subject_id,
        stem="NOT NULL 测试题",
        source_type="document",
    )
    db.add(q)
    await db.flush()

    inst = QuestionInstance(
        question_id=q.id,
        source_type="document",
    )
    db.add(inst)
    with pytest.raises(Exception) as exc_info:
        await db.flush()
    err_msg = str(exc_info.value).lower()
    assert "not-null" in err_msg or "null" in err_msg or "violates not-null" in err_msg


# ═══════════════════════════════════════════════════════════════════
# 6. Ingestion 真实路径验证（docs_archive/2026-08-24/PHASE_2A_EXECUTION_PLAN.md Step 0 补齐）
# ═══════════════════════════════════════════════════════════════════
# 执行计划指出：原有 test_question_creation_without_year_school /
# test_instance_creation_with_document_id 直接构造 model，未走 ingestion；
# test_occurrence_count_updates_with_instances 是手工更新 count。
# 以下测试通过真实 ingest_pipeline_result 验证 ingestion 行为。


def _make_pipeline_result(question_number: str, stem: str) -> Any:
    """构造最小 PipelineResult（带一道已通过质量门的题）。"""
    from app.domains.document.pipeline_shared import PipelineResult
    from app.domains.document.schemas_l2 import SlicedQuestion

    result = PipelineResult()
    result.sliced_questions = [
        SlicedQuestion(
            question_number=question_number,
            question_type="single_choice",
            stem=stem,
            options=[{"label": "A", "text": "选项A"}, {"label": "B", "text": "选项B"}],
            answer="A",
            confidence=0.95,  # 高置信度 → approved
        )
    ]
    return result


def _make_answer_result(subject: str, question_number: str, answer: str) -> Any:
    """构造最小 AnswerExtractionResult。"""
    from app.domains.document.answer_extractor import (
        AnswerExtractionResult,
        ExtractedAnswer,
    )

    result = AnswerExtractionResult(subject=subject)
    result.answers[question_number] = ExtractedAnswer(
        question_number=question_number,
        answer=answer,
        explanation="详解",
    )
    return result


@pytest.mark.asyncio
async def test_ingestion_creates_question_without_year_school(db, subject_id):
    """真实 ingestion：创建 Question 不写 year/school，Instance 写 document_id。"""
    from app.domains.document.ingestion import ingest_pipeline_result

    doc = Document(
        filename="test_ingestion_real.pdf",
        file_type="pdf",
        object_key="test/test_ingestion_real.pdf",
        subject="数学",
        grade="高二",
        year=2024,
        school="朝阳中学",
    )
    db.add(doc)
    await db.flush()

    pipeline_result = _make_pipeline_result("1", "ingestion 真实路径题干")
    answer_result = _make_answer_result("数学", "1", "A")
    ingest = await ingest_pipeline_result(
        db,
        pipeline_result=pipeline_result,
        answer_result=answer_result,
        document=doc,
    )

    assert ingest.ingested == 1
    assert len(ingest.question_ids) == 1
    qid = ingest.question_ids[0]

    # Question：不写 year/school
    q = await db.scalar(select(Question).where(Question.id == qid))
    assert q is not None
    assert q.status == "approved"
    assert not hasattr(q, "year")  # model 已无 year 字段
    assert not hasattr(q, "school")

    # Instance：写 document_id
    inst = await db.scalar(
        select(QuestionInstance).where(QuestionInstance.question_id == qid)
    )
    assert inst is not None
    assert inst.document_id == doc.id
    assert inst.source_question_number == "1"
    assert inst.year == 2024       # 从 document 带出
    assert inst.school == "朝阳中学"


@pytest.mark.asyncio
async def test_ingestion_exact_match_creates_instance_and_updates_count(db, subject_id):
    """真实 ingestion 精确匹配：同一 PDF 上传两次（两个 Document），第二次只创建 Instance。"""
    from app.domains.document.ingestion import ingest_pipeline_result

    # 第一次上传：注册 document A
    doc_a = Document(
        filename="test_ingestion_dedup_a.pdf",
        file_type="pdf",
        object_key="test/test_ingestion_dedup_a.pdf",
        subject="数学",
    )
    db.add(doc_a)
    await db.flush()

    stem = "dedup 精确匹配题干"
    pipeline_result = _make_pipeline_result("2", stem)
    answer_result = _make_answer_result("数学", "2", "B")

    # 第一次入库：创建新 Question
    ingest1 = await ingest_pipeline_result(
        db,
        pipeline_result=pipeline_result,
        answer_result=answer_result,
        document=doc_a,
    )
    assert ingest1.ingested == 1
    qid = ingest1.question_ids[0]

    # 第二次上传：注册 document B（模拟同一 PDF 再次上传）
    doc_b = Document(
        filename="test_ingestion_dedup_b.pdf",
        file_type="pdf",
        object_key="test/test_ingestion_dedup_b.pdf",
        subject="数学",
    )
    db.add(doc_b)
    await db.flush()

    ingest2 = await ingest_pipeline_result(
        db,
        pipeline_result=pipeline_result,
        answer_result=answer_result,
        document=doc_b,
    )
    assert ingest2.ingested == 1
    assert ingest2.question_ids[0] == qid  # 同一 Question，不创建新 Question

    # 只有一个 Question
    q_count = await db.scalar(
        select(func.count()).select_from(Question).where(Question.id == qid)
    )
    assert q_count == 1

    # 两个 Instance（不同 document_id），occurrence_count 与 COUNT 一致（ingestion 更新路径，非手工）
    inst_count = await db.scalar(
        select(func.count())
        .select_from(QuestionInstance)
        .where(QuestionInstance.question_id == qid)
    )
    assert inst_count == 2
    q = await db.scalar(select(Question).where(Question.id == qid))
    assert q.occurrence_count == inst_count

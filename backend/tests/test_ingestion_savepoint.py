"""P0-A 测试：ingestion 逐题 savepoint 事务隔离。

验证：
1. 单题 UniqueViolationError 不毒化 session，其他题目正常入库
2. 失败的题目被记录在 IngestionResult.errors 中
3. 成功入库的题目在外层事务提交后持久化
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.domains.document.ingestion import ingest_pipeline_result, IngestionResult
from app.domains.document.pipeline_shared import PipelineResult
from app.domains.document.schemas_l1 import L1Document, L1Line, L1Page
from app.domains.document.schemas_l2 import CorrectedAnchor, L2SubQuestion, SlicedQuestion
from app.models import Document, Question, QuestionInstance


@pytest_asyncio.fixture
async def db():
    """真实 PostgreSQL 事务回滚隔离。"""
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.connect() as conn:
        async with conn.begin() as transaction:
            session = AsyncSession(bind=conn, expire_on_commit=False)
            yield session
            await transaction.rollback()
    await engine.dispose()


def _make_document(db) -> Document:
    doc = Document(
        filename="test_savepoint.pdf",
        file_type="pdf",
        object_key="test/savepoint",
        subject="数学",
        grade="高一",
        processing_status="processing",
    )
    db.add(doc)
    return doc


def _make_question(qno: str, stem: str = "test stem") -> SlicedQuestion:
    """构造最小可入库的 SlicedQuestion。"""
    from app.domains.document.schemas_l2 import SourceProvenance
    anchor = CorrectedAnchor(
        field="stem",
        llm_line_ids=["P1L001"],
        corrected_line_ids=["P1L001"],
        anchor_status="exact",
        validation_passed=True,
    )
    return SlicedQuestion(
        question_number=qno,
        question_type="single_choice",
        stem=stem,
        options=[{"label": "A", "text": "opt1"}, {"label": "B", "text": "opt2"},
                 {"label": "C", "text": "opt3"}, {"label": "D", "text": "opt4"}],
        confidence=0.9,
        answer="A",
        answer_provenance=SourceProvenance("answer", "document_answer_table", 1.0),
        stem_anchor=anchor,
        corrected_anchors=[anchor],
        stem_line_ids=["P1L001"],
        answer_line_ids=["P2L001"],
        section_id="section_1",
        score=3.0,
        difficulty=2,
        knowledge_points=["知识点A"],
    )


def _make_pipeline_result(questions: list[SlicedQuestion]) -> PipelineResult:
    lines = []
    for i, q in enumerate(questions):
        line = L1Line(
            line_id=f"P1L{i+1:03d}", page_no=1, line_no_in_page=i+1, order=i+1,
            text=q.stem or "test", block_type="text",
            bbox={"x1": 0, "y1": 0, "x2": 100, "y2": 20},
            source="ppsv3",
        )
        lines.append(line)
        # 更新 stem_line_ids 以匹配生成的行 ID
        q.stem_line_ids = [f"P1L{i+1:03d}"]

    l1_doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        images=[],
        source="ppsv3",
        total_pages=1,
    )
    result = PipelineResult()
    result.status = "succeeded"
    result.sliced_questions = questions
    result.l1_document = l1_doc
    result.question_images = []
    return result


class TestIngestionSavepointIsolation:
    """P0-A: 逐题 savepoint 事务隔离。"""

    @pytest.mark.asyncio
    async def test_single_failure_does_not_poison_session(self, db):
        """一道题的 UniqueViolationError 不影响其他题目入库。"""
        document = _make_document(db)
        await db.flush()

        # Q1 和 Q2 是正常题目
        q1 = _make_question("1", "Q1 stem")
        q2 = _make_question("2", "Q2 stem")
        # Q3 也是正常题目
        q3 = _make_question("3", "Q3 stem")

        # 先手动插入一个 source_question_number='4' 的 Instance，模拟已有记录
        from app.models import Subject
        subj = Subject(code="test_math", name="数学")
        db.add(subj)
        await db.flush()

        existing_q = Question(
            subject_id=subj.id,
            stem="existing Q4",
            question_type_id=None,
            status="approved",
            confidence=0.9,
            source_type="document",
            source_document_name="other.pdf",
        )
        db.add(existing_q)
        await db.flush()

        existing_inst = QuestionInstance(
            question_id=existing_q.id,
            document_id=document.id,
            source_type="document",
            source_document_name="other.pdf",
            source_question_number="4",
            occurrence_no=1,
        )
        db.add(existing_inst)
        await db.flush()

        # Q4 会触发 UniqueViolationError（同 document_id + source_question_number='4'）
        q4 = _make_question("4", "Q4 stem — will collide")

        pipeline = _make_pipeline_result([q1, q2, q3, q4])
        result = await ingest_pipeline_result(
            db,
            pipeline_result=pipeline,
            document=document,
        )

        # Q1, Q2, Q3 应成功；Q4 应失败
        assert result.ingested >= 3, (
            f"至少 3 题应成功入库，实际 ingested={result.ingested}, "
            f"failed={result.failed}, errors={result.errors}"
        )
        assert result.failed >= 1, f"Q4 应失败，实际 failed={result.failed}"

        # session 不应被毒化 — 能正常执行查询
        count = await db.scalar(
            text("SELECT COUNT(*) FROM question_instances WHERE document_id = :doc_id"),
            {"doc_id": str(document.id)},
        )
        assert count >= 3, f"至少 3 个 Instance 应存在，实际 {count}"

    @pytest.mark.asyncio
    async def test_all_questions_fail_gracefully(self, db):
        """所有题目都失败时，session 仍可用（不 PendingRollbackError）。"""
        document = _make_document(db)
        await db.flush()

        # 创建 3 个同题号的 SlicedQuestion（模拟全部重复）
        from app.models import Subject
        subj = Subject(code="test_math2", name="数学")
        db.add(subj)
        await db.flush()

        existing_q = Question(
            subject_id=subj.id,
            stem="existing",
            question_type_id=None,
            status="approved",
            confidence=0.9,
            source_type="document",
            source_document_name="other.pdf",
        )
        db.add(existing_q)
        await db.flush()

        existing_inst = QuestionInstance(
            question_id=existing_q.id,
            document_id=document.id,
            source_type="document",
            source_document_name="other.pdf",
            source_question_number="1",
            occurrence_no=1,
        )
        db.add(existing_inst)
        await db.flush()

        # 3 道题都用 question_number='1'（全会冲突）
        qs = [_make_question("1", f"Q1 stem variant {i}") for i in range(3)]
        pipeline = _make_pipeline_result(qs)

        result = await ingest_pipeline_result(
            db,
            pipeline_result=pipeline,
            document=document,
        )

        assert result.ingested == 0
        assert result.failed == 3

        # session 不被毒化 — 能正常查询
        count = await db.scalar(text("SELECT COUNT(*) FROM documents"))
        assert count >= 1

    @pytest.mark.asyncio
    async def test_mixed_success_and_duplicate(self, db):
        """混合场景：正常题 + 重复题 + 后续正常题，后续正常题不被拖垮。"""
        document = _make_document(db)
        await db.flush()

        from app.models import Subject
        subj = Subject(code="test_math3", name="数学")
        db.add(subj)
        await db.flush()

        # 预置 Q5 已存在
        existing_q = Question(
            subject_id=subj.id,
            stem="existing Q5",
            question_type_id=None,
            status="approved",
            confidence=0.9,
            source_type="document",
            source_document_name="other.pdf",
        )
        db.add(existing_q)
        await db.flush()
        existing_inst = QuestionInstance(
            question_id=existing_q.id,
            document_id=document.id,
            source_type="document",
            source_document_name="other.pdf",
            source_question_number="5",
            occurrence_no=1,
        )
        db.add(existing_inst)
        await db.flush()

        # Q1-Q4 正常，Q5 重复，Q6-Q8 正常
        qs = [_make_question(str(i), f"Q{i} stem") for i in range(1, 9)]
        # Q5 的 question_number='5' 会冲突
        pipeline = _make_pipeline_result(qs)

        result = await ingest_pipeline_result(
            db,
            pipeline_result=pipeline,
            document=document,
        )

        # Q1-Q4 + Q6-Q8 = 7 题成功，Q5 失败
        assert result.ingested >= 7, (
            f"至少 7 题应成功（Q1-4,Q6-8），实际 ingested={result.ingested}, "
            f"failed={result.failed}, errors={result.errors}"
        )
        assert result.failed >= 1

@pytest.mark.asyncio
async def test_persists_original_question_type_and_section(db):
    """Ingestion persists fine-grained type and section_id into questions."""
    document = _make_document(db)
    await db.flush()
    q = _make_question("1", "Q1 original type")
    q.original_question_type = "cloze"
    q.section_id = "cloze_1"
    result = await ingest_pipeline_result(
        db,
        pipeline_result=_make_pipeline_result([q]),
        document=document,
    )
    assert result.ingested >= 1
    saved = await db.scalar(select(Question).where(Question.stem == "Q1 original type"))
    assert saved is not None
    assert saved.original_question_type == "cloze"
    assert saved.section_id == "cloze_1"

@pytest.mark.asyncio
async def test_persists_nested_sub_questions(db):
    """Ingestion persists recursive sub_questions into questions JSONB."""
    document = _make_document(db)
    await db.flush()
    q = _make_question("1", "Q1 nested")
    q.sub_questions = [
        L2SubQuestion(
            qno="(3)",
            question_type="short_answer",
            sub_sub_questions=[L2SubQuestion(qno="i", question_type="short_answer", answer="x")],
        )
    ]
    result = await ingest_pipeline_result(
        db,
        pipeline_result=_make_pipeline_result([q]),
        document=document,
    )
    assert result.ingested >= 1
    saved = await db.scalar(select(Question).where(Question.stem == "Q1 nested"))
    assert saved is not None
    assert saved.sub_questions[0]["sub_sub_questions"][0]["qno"] == "i"

def test_build_answer_structure_range_and_accepted():
    """Range and multi-answer strings produce structured answer metadata."""
    from app.domains.document.ingestion import _build_answer_structure

    assert _build_answer_structure("24.00~25.00") == {"range": {"min": "24.00", "max": "25.00"}}
    assert _build_answer_structure("that/which") == {"accepted_answers": ["that", "which"]}
    assert _build_answer_structure("plain answer") is None
    assert _build_answer_structure("因为天气或交通原因") is None
    assert _build_answer_structure("A；B") == {"accepted_answers": ["A", "B"]}
    assert _build_answer_structure("25.00～26.00") == {"range": {"min": "25.00", "max": "26.00"}}
    assert _build_answer_structure("A|B|C") == {"accepted_answers": ["A", "B", "C"]}
    assert _build_answer_structure(None) is None
    assert _build_answer_structure("") is None
    assert _build_answer_structure("见解析") is None


@pytest.mark.asyncio
async def test_persists_answer_structure(db):
    """Ingestion persists structured answer metadata into questions JSONB."""
    document = _make_document(db)
    await db.flush()
    q = _make_question("1", "Q1 answer structure")
    q.answer = "that/which"
    q.answer_structure = {"accepted_answers": ["that", "which"]}
    result = await ingest_pipeline_result(
        db,
        pipeline_result=_make_pipeline_result([q]),
        document=document,
    )
    assert result.ingested >= 1
    saved = await db.scalar(select(Question).where(Question.stem == "Q1 answer structure"))
    assert saved is not None
    assert saved.answer_structure == {"accepted_answers": ["that", "which"]}

@pytest.mark.asyncio
async def test_persists_word_bank(db):
    """Ingestion persists word_bank JSONB."""
    document = _make_document(db)
    await db.flush()
    q = _make_question("1", "Q1 word bank")
    q.word_bank = ["pack", "confuse"]
    result = await ingest_pipeline_result(
        db,
        pipeline_result=_make_pipeline_result([q]),
        document=document,
    )
    assert result.ingested >= 1
    saved = await db.scalar(select(Question).where(Question.stem == "Q1 word bank"))
    assert saved is not None
    assert saved.word_bank == ["pack", "confuse"]

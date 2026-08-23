"""
Phase 2A Step 4 集成测试 — 答案重试关联修正。

覆盖（PHASE_2A_EXECUTION_PLAN.md Step 4 必须新增测试）：
1. 同一文档有 3 道空答案题，重试后每道题更新到正确 Question
2. 不同文档有相同题号时，不会互相污染
3. document_id 或 source_question_number 找不到 Instance 时，记录失败而不是更新错误题目

真实 PostgreSQL 集成测试（每个测试函数独立事务回滚），LLM 答案提取用 mock。
"""
import uuid

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.domains.document.answer_extractor import AnswerExtractionResult, ExtractedAnswer
from app.domains.document.retry_repository import AnswerExtractionRetryRepository
from app.models import (
    AnswerExtractionRetry,
    Document,
    Question,
    QuestionInstance,
)


# ── Fixtures ──────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def async_engine():
    engine = create_async_engine(settings.database_url, echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db(async_engine):
    """带事务的 session，测试结束自动回滚。"""
    async with async_engine.connect() as conn:
        async with conn.begin() as transaction:
            session = AsyncSession(bind=conn, expire_on_commit=False)
            yield session
            await transaction.rollback()


@pytest_asyncio.fixture
async def subject_id(db):
    """创建一个测试学科。"""
    from app.models import Subject

    subj = Subject(code=f"test_step4_{uuid.uuid4().hex[:8]}", name="测试学科_Step4")
    db.add(subj)
    await db.flush()
    return subj.id


async def _make_doc_with_empty_questions(db, subject_id, *, filename: str, qnos: list[str]):
    """构造 document + 每道空答案题的 question + instance，返回 (doc, {qno: question})。"""
    from app.models import Document

    doc = Document(
        filename=filename,
        file_type="pdf",
        object_key=f"test/{filename}",
        subject="数学",
        ocr_markdown="# 测试文档\n1. 题干一\n2. 题干二\n3. 题干三\n",
    )
    db.add(doc)
    await db.flush()

    questions = {}
    for qno in qnos:
        q = Question(
            subject_id=subject_id,
            stem=f"{filename} 第{qno}题",
            source_type="document",
            source_document_name=filename,
            status="reviewing",
            occurrence_count=1,
            answer=None,  # 空答案，等待重试填充
        )
        db.add(q)
        await db.flush()
        inst = QuestionInstance(
            question_id=q.id,
            document_id=doc.id,
            source_type="document",
            source_document_name=filename,
            source_question_number=qno,
            occurrence_no=1,
        )
        db.add(inst)
        questions[qno] = q
    await db.flush()
    return doc, questions


def _make_answer_result(answers: dict[str, str]) -> AnswerExtractionResult:
    """构造答案提取结果：{题号: 答案}。"""
    result = AnswerExtractionResult(subject="数学")
    for qno, ans in answers.items():
        result.answers[qno] = ExtractedAnswer(
            question_number=qno,
            answer=ans,
            explanation=f"{qno} 的详解",
        )
    return result


def _make_retry_item(db, document_id, task_id=None):
    """创建 retry 记录并返回。"""
    item = AnswerExtractionRetry(
        document_id=document_id,
        task_id=task_id,
        status="pending",
        error_detail="original failure",
    )
    db.add(item)
    return item


# ═══════════════════════════════════════════════════════════════════
# 1. 同一文档 3 道空答案题 → 每道更新到正确 Question
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_retry_updates_each_question_correctly(db, subject_id):
    """同一文档 3 道空答案题，重试后每道题更新到正确 Question（按题号精确关联）。"""
    from app.worker.answer_retry_worker import _process_one_retry

    doc, questions = await _make_doc_with_empty_questions(
        db, subject_id, filename=f"retry_a_{uuid.uuid4().hex[:6]}.pdf",
        qnos=["1", "2", "3"],
    )
    item = _make_retry_item(db, doc.id)
    await db.flush()

    repo = AnswerExtractionRetryRepository(db)
    # mock gateway：直接返回答案映射
    fake_gateway = MagicMock()

    with patch(
        "app.worker.answer_retry_worker.extract_answers_from_markdown",
        AsyncMock(return_value=_make_answer_result({"1": "A", "2": "B", "3": "C"})),
    ):
        await _process_one_retry(db, repo, item, fake_gateway)

    # 每道题更新到正确 Question
    q1 = await db.scalar(select(Question).where(Question.id == questions["1"].id))
    q2 = await db.scalar(select(Question).where(Question.id == questions["2"].id))
    q3 = await db.scalar(select(Question).where(Question.id == questions["3"].id))
    assert q1.answer == "A"
    assert q2.answer == "B"
    assert q3.answer == "C"
    # 详解同步
    assert q1.explanation == "1 的详解"
    # retry 标记成功
    assert item.status == "succeeded"


# ═══════════════════════════════════════════════════════════════════
# 2. 不同文档相同题号 → 不互相污染
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_retry_does_not_pollute_other_documents(db, subject_id):
    """不同文档有相同题号时，只更新本 document 的题目。"""
    from app.worker.answer_retry_worker import _process_one_retry

    doc_a, qa = await _make_doc_with_empty_questions(
        db, subject_id, filename=f"retry_docA_{uuid.uuid4().hex[:6]}.pdf", qnos=["1"],
    )
    doc_b, qb = await _make_doc_with_empty_questions(
        db, subject_id, filename=f"retry_docB_{uuid.uuid4().hex[:6]}.pdf", qnos=["1"],
    )
    item = _make_retry_item(db, doc_a.id)
    await db.flush()

    repo = AnswerExtractionRetryRepository(db)
    fake_gateway = MagicMock()

    with patch(
        "app.worker.answer_retry_worker.extract_answers_from_markdown",
        AsyncMock(return_value=_make_answer_result({"1": "A"})),
    ):
        await _process_one_retry(db, repo, item, fake_gateway)

    q_a = await db.scalar(select(Question).where(Question.id == qa["1"].id))
    q_b = await db.scalar(select(Question).where(Question.id == qb["1"].id))
    assert q_a.answer == "A"        # doc_a 的题号 1 被更新
    assert q_b.answer is None       # doc_b 的题号 1 不被污染


# ═══════════════════════════════════════════════════════════════════
# 3. 找不到 Instance → 记录失败，不更新错误题目
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_retry_missing_instance_marks_failed(db, subject_id):
    """document_id + source_question_number 找不到 Instance → 记录失败，不更新错误题目。"""
    from app.worker.answer_retry_worker import _process_one_retry

    doc, questions = await _make_doc_with_empty_questions(
        db, subject_id, filename=f"retry_miss_{uuid.uuid4().hex[:6]}.pdf", qnos=["1"],
    )
    item = _make_retry_item(db, doc.id)
    await db.flush()

    repo = AnswerExtractionRetryRepository(db)
    fake_gateway = MagicMock()

    # 答案提取返回了文档中不存在的题号 "99"（没有对应 instance）
    with patch(
        "app.worker.answer_retry_worker.extract_answers_from_markdown",
        AsyncMock(return_value=_make_answer_result({"99": "X"})),
    ):
        await _process_one_retry(db, repo, item, fake_gateway)

    # retry 标记失败（找不到 instance）
    assert item.status == "failed"
    assert "not found via question_instances" in (item.error_detail or "")
    # 文档中已有的题目未被错误更新
    q1 = await db.scalar(select(Question).where(Question.id == questions["1"].id))
    assert q1.answer is None


@pytest.mark.asyncio
async def test_retry_document_not_found_marks_failed(db, subject_id):
    """document 存在但无 ocr_markdown → 记录失败（不进入答案提取）。"""
    from app.worker.answer_retry_worker import _process_one_retry

    doc = Document(
        filename=f"retry_nomd_{uuid.uuid4().hex[:6]}.pdf",
        file_type="pdf",
        object_key="test/nomd.pdf",
        subject="数学",
        ocr_markdown=None,  # 无 OCR markdown
    )
    db.add(doc)
    await db.flush()

    item = _make_retry_item(db, doc.id)
    await db.flush()

    repo = AnswerExtractionRetryRepository(db)
    fake_gateway = MagicMock()

    await _process_one_retry(db, repo, item, fake_gateway)

    assert item.status == "failed"
    assert "document or ocr_markdown not found" in (item.error_detail or "")


# ═══════════════════════════════════════════════════════════════════
# 4. 已有答案不覆盖（保留人工/管线结果）
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_retry_does_not_overwrite_existing_answer(db, subject_id):
    """已有答案的题目不被 retry 覆盖（只填充空答案）。"""
    from app.worker.answer_retry_worker import _process_one_retry

    doc, questions = await _make_doc_with_empty_questions(
        db, subject_id, filename=f"retry_keep_{uuid.uuid4().hex[:6]}.pdf", qnos=["1"],
    )
    # 给题号 1 已有答案（模拟人工审核或管线结果）
    questions["1"].answer = "D"
    await db.flush()

    item = _make_retry_item(db, doc.id)
    await db.flush()

    repo = AnswerExtractionRetryRepository(db)
    fake_gateway = MagicMock()

    with patch(
        "app.worker.answer_retry_worker.extract_answers_from_markdown",
        AsyncMock(return_value=_make_answer_result({"1": "A"})),
    ):
        await _process_one_retry(db, repo, item, fake_gateway)

    q1 = await db.scalar(select(Question).where(Question.id == questions["1"].id))
    assert q1.answer == "D"  # 保留已有答案


@pytest.mark.asyncio
async def test_retry_extraction_failure_does_not_stick_retrying(db, subject_id):
    """LLM 答案提取异常时，未超限恢复 pending，超限才标记 failed。"""
    from app.worker.answer_retry_worker import _process_one_retry
    from app.models import Document

    doc = Document(
        filename=f"retry_fail_{uuid.uuid4().hex[:6]}.pdf",
        file_type="pdf",
        object_key="test/retry_fail.pdf",
        subject="数学",
        ocr_markdown="1. 题干\n2. 题干\n3. 题干\n",
    )
    db.add(doc)
    await db.flush()

    item = AnswerExtractionRetry(
        document_id=doc.id,
        status="pending",
        max_retries=2,
    )
    db.add(item)
    await db.flush()

    repo = AnswerExtractionRetryRepository(db)
    fake_gateway = MagicMock()

    with patch(
        "app.worker.answer_retry_worker.extract_answers_from_markdown",
        AsyncMock(side_effect=RuntimeError("llm failed")),
    ):
        await _process_one_retry(db, repo, item, fake_gateway)
    assert item.status == "pending", (
        f"未超限应恢复 pending，实际 {item.status}，retry_count={item.retry_count}"
    )
    assert item.retry_count == 1

    with patch(
        "app.worker.answer_retry_worker.extract_answers_from_markdown",
        AsyncMock(side_effect=RuntimeError("llm failed")),
    ):
        await _process_one_retry(db, repo, item, fake_gateway)

    assert item.status == "failed"
    assert item.retry_count == 2

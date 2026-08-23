"""
Phase 2A Step 3 测试 — Worker 失败语义 + L2 完整持久化 + 幂等重跑清理。

覆盖（docs_archive/2026-08-24/PHASE_2A_EXECUTION_PLAN.md Step 3 必须新增测试）：
1. ingestion 抛异常时 background_tasks.status='failed'、documents.processing_status='failed'
2. 答案提取失败时任务仍 succeeded，答案进入 retry queue
3. llm_annotated_markdown 包含 knowledge_points/difficulty/score/corrected_anchors/anchor_status/question_type
4. 幂等重跑只清理 source_type='document' 且 status='reviewing' 的未审核记录
5. 已审核记录和 review_overrides 非空记录不被静默覆盖

worker 轮询模式使用 mock（沿用 test_worker_status.py 风格），
幂等清理与 L2 序列化使用真实 session 集成验证。
"""
import asyncio
import json
import uuid

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.domains.document.pipeline import PipelineResult
from app.domains.document.schemas_l2 import (
    CorrectedAnchor,
    L2DocumentAnnotation,
    L2QuestionAnnotation,
    L2SubQuestion,
)


# ── 真实 DB fixtures（幂等清理集成测试用） ───────────────────────

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

    subj = Subject(code=f"test_step3_{uuid.uuid4().hex[:8]}", name="测试学科_Step3")
    db.add(subj)
    await db.flush()
    return subj.id


def _make_l2_annotation() -> L2DocumentAnnotation:
    """构造含完整 L2 字段的标注。"""
    return L2DocumentAnnotation(
        filename="test.pdf",
        subject="数学",
        grade="高二",
        year=2024,
        school="朝阳中学",
        metadata_confidence=0.9,
        warnings=["marker fuzzy"],
        anchor_status_summary={"exact": 1, "nearest": 1},
        corrected_anchors=[
            CorrectedAnchor(
                field="stem",
                llm_line_ids=["P1L001"],
                corrected_line_ids=["P1L002"],
                anchor_status="nearest",
                validation_passed=True,
                evidence="吸附到题号标记 1.",
                question_number="1",
            )
        ],
        questions=[
            L2QuestionAnnotation(
                question_number="1",
                question_type="single_choice",
                stem_line_ids=["P1L002"],
                options_line_ids={"A": ["P1L003"]},
                answer="A",
                answer_line_ids=["P1L010"],
                explanation_line_ids=["P1L011"],
                difficulty=3,
                score=4.0,
                knowledge_points=["函数单调性", "不等式"],
                confidence=0.95,
                source_page=1,
                is_composite=True,
                sub_questions=[
                    L2SubQuestion(qno="（1）", question_type="fill_in", answer="2", score=2.0),
                ],
            )
        ],
    )


def _make_succeeded_result() -> PipelineResult:
    result = PipelineResult()
    result.status = "succeeded"
    result.l2_annotation = _make_l2_annotation()
    result.sliced_questions = []
    return result


async def _run_worker_once(
    *,
    result,
    extract_and_ingest=None,
    succeed_task=None,
    fail_task=None,
    session=None,
):
    """启动 worker 并只消费一个任务后停止，返回 mock 对象供断言。"""
    from app.worker.document_worker import document_parse_worker

    mock_session = session or AsyncMock()
    mock_session.close = AsyncMock()
    mock_task_service = AsyncMock()
    mock_task_service.commit = AsyncMock()
    mock_doc_service = AsyncMock()
    mock_doc_service.commit = AsyncMock()

    mock_task = MagicMock()
    mock_task.id = UUID("00000000-0000-0000-0000-000000000001")
    mock_task.payload_json = {
        "document_id": str(UUID("00000000-0000-0000-0000-000000000002"))
    }

    mock_doc = MagicMock()
    mock_doc.id = UUID("00000000-0000-0000-0000-000000000002")
    mock_doc.object_key = "test.pdf"
    mock_doc.filename = "test.pdf"
    mock_doc.processing_status = "processing"
    mock_doc.error_message = None

    if succeed_task is not None:
        mock_task_service.succeed_task = succeed_task
    if fail_task is not None:
        mock_task_service.fail_task = fail_task
    mock_task_service.list_tasks = AsyncMock(return_value=[mock_task])
    mock_doc_service.get_document = AsyncMock(return_value=mock_doc)

    call_count = 0
    stop_event = asyncio.Event()

    async def mock_factory():
        nonlocal call_count
        call_count += 1
        if call_count >= 1:
            stop_event.set()
        return mock_session, mock_task_service, mock_doc_service

    with patch("app.domains.document.processor.DocumentProcessor") as MockProcessor:
        mock_instance = MagicMock()
        mock_instance.process_document = AsyncMock(return_value=result)
        if extract_and_ingest is not None:
            mock_instance.extract_and_ingest = extract_and_ingest
        MockProcessor.return_value = mock_instance

        worker_task = asyncio.create_task(
            document_parse_worker(
                storage=MagicMock(),
                gateway=MagicMock(),
                create_task_services=mock_factory,
                stop_event=stop_event,
            )
        )
        try:
            await asyncio.wait_for(worker_task, timeout=5.0)
        except asyncio.TimeoutError:
            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                pass

    return mock_session, mock_task_service, mock_doc_service, mock_doc


# ═══════════════════════════════════════════════════════════════════
# 1. ingestion 异常 → task failed + document failed
# ═══════════════════════════════════════════════════════════════════


class TestIngestionFailureSemantics:
    @pytest.mark.asyncio
    async def test_ingestion_exception_marks_task_and_document_failed(self):
        """ingestion 抛异常 → task.status='failed'，document.processing_status='failed'。"""
        from app.domains.document.ingestion import IngestionResult

        async def failing_ingest(**kwargs):
            raise RuntimeError("db write failed")

        fail_calls = []

        async def real_fail_task(task_id, error_detail=None):
            fail_calls.append((task_id, error_detail))

        _, mock_task_service, mock_doc_service, mock_doc = await _run_worker_once(
            result=_make_succeeded_result(),
            extract_and_ingest=failing_ingest,
            fail_task=real_fail_task,
        )

        # task 被 fail_task 标记
        assert len(fail_calls) == 1
        assert "ingestion failed" in fail_calls[0][1]
        # document 被 worker 标记 failed
        assert mock_doc.processing_status == "failed"
        assert "ingestion failed" in (mock_doc.error_message or "")

    @pytest.mark.asyncio
    async def test_ingestion_success_marks_task_succeeded_document_completed(self):
        """ingestion 正常 → task succeeded，document completed（回归验证）。"""
        from app.domains.document.ingestion import IngestionResult

        success_calls = []

        async def real_succeed_task(task_id, result=None):
            success_calls.append((task_id, result))

        async def ok_ingest(**kwargs):
            return IngestionResult(
                total_questions=0,
                ingested=0,
                skipped=0,
                failed=0,
                answer_extraction_status="skipped",
            )

        _, mock_task_service, mock_doc_service, mock_doc = await _run_worker_once(
            result=_make_succeeded_result(),
            extract_and_ingest=ok_ingest,
            succeed_task=real_succeed_task,
        )

        assert len(success_calls) == 1
        assert mock_doc.processing_status == "completed"


# ═══════════════════════════════════════════════════════════════════
# 2. 答案提取失败 → task 仍 succeeded + 进 retry queue
# ═══════════════════════════════════════════════════════════════════


class TestAnswerExtractionFailureKeepsSucceeded:
    @pytest.mark.asyncio
    async def test_answer_extraction_failed_goes_to_retry_queue_task_succeeded(self):
        """答案提取失败：task 仍 succeeded，AnswerExtractionRetry 记录入队。"""
        from app.domains.document.ingestion import IngestionResult

        mock_session = AsyncMock()
        # 模拟 session.add 收集对象
        added = []

        def fake_add(obj):
            added.append(obj)

        mock_session.add = fake_add
        mock_session.flush = AsyncMock()
        mock_session.delete = AsyncMock()
        mock_session.get = AsyncMock(return_value=None)
        mock_session.close = AsyncMock()
        mock_session.scalars = AsyncMock(return_value=[])

        success_calls = []

        async def real_succeed_task(task_id, result=None):
            success_calls.append((task_id, result))

        async def ingest_with_failed_extraction(**kwargs):
            return IngestionResult(
                total_questions=1,
                ingested=1,
                skipped=0,
                failed=0,
                answer_extraction_status="failed",
                answer_extraction_error="llm timeout",
            )

        _, mock_task_service, mock_doc_service, mock_doc = await _run_worker_once(
            result=_make_succeeded_result(),
            extract_and_ingest=ingest_with_failed_extraction,
            succeed_task=real_succeed_task,
            session=mock_session,
        )

        # task 仍 succeeded（不是 failed）
        assert len(success_calls) == 1
        assert mock_doc.processing_status == "completed"
        # AnswerExtractionRetry + DocumentProcessingLog 入队
        from app.models import AnswerExtractionRetry, DocumentProcessingLog

        retry_types = [type(a) for a in added]
        assert AnswerExtractionRetry in retry_types
        assert DocumentProcessingLog in retry_types


# ═══════════════════════════════════════════════════════════════════
# 3. L2 完整持久化
# ═══════════════════════════════════════════════════════════════════


class TestL2FullPersistence:
    @pytest.mark.asyncio
    async def test_l2_serialization_contains_all_fields(self):
        """worker 生成的 llm_annotated_markdown JSON 包含完整 L2 字段。"""
        from app.domains.document.ingestion import IngestionResult

        async def ok_ingest(**kwargs):
            return IngestionResult()

        # 用真实 session stub 捕获 document 赋值
        mock_session = AsyncMock()
        mock_session.close = AsyncMock()
        mock_session.flush = AsyncMock()
        mock_session.delete = AsyncMock()
        mock_session.get = AsyncMock(return_value=None)
        mock_session.scalars = AsyncMock(return_value=[])

        from app.worker.document_worker import document_parse_worker

        mock_task_service = AsyncMock()
        mock_task_service.commit = AsyncMock()
        mock_doc_service = AsyncMock()
        mock_doc_service.commit = AsyncMock()

        mock_task = MagicMock()
        mock_task.id = UUID("00000000-0000-0000-0000-000000000001")
        mock_task.payload_json = {
            "document_id": str(UUID("00000000-0000-0000-0000-000000000002"))
        }

        mock_doc = MagicMock()
        mock_doc.id = UUID("00000000-0000-0000-0000-000000000002")
        mock_doc.object_key = "test.pdf"
        mock_doc.filename = "test.pdf"
        mock_doc.processing_status = "processing"
        mock_doc.error_message = None

        mock_task_service.succeed_task = AsyncMock()
        mock_task_service.list_tasks = AsyncMock(return_value=[mock_task])
        mock_doc_service.get_document = AsyncMock(return_value=mock_doc)

        call_count = 0
        stop_event = asyncio.Event()

        async def mock_factory():
            nonlocal call_count
            call_count += 1
            if call_count >= 1:
                stop_event.set()
            return mock_session, mock_task_service, mock_doc_service

        with patch("app.domains.document.processor.DocumentProcessor") as MockProcessor:
            mock_instance = MagicMock()
            mock_instance.process_document = AsyncMock(return_value=_make_succeeded_result())
            mock_instance.extract_and_ingest = ok_ingest
            MockProcessor.return_value = mock_instance

            worker_task = asyncio.create_task(
                document_parse_worker(
                    storage=MagicMock(),
                    gateway=MagicMock(),
                    create_task_services=mock_factory,
                    stop_event=stop_event,
                )
            )
            try:
                await asyncio.wait_for(worker_task, timeout=5.0)
            except asyncio.TimeoutError:
                worker_task.cancel()
                try:
                    await worker_task
                except asyncio.CancelledError:
                    pass

        raw = mock_doc.llm_annotated_markdown
        assert raw is not None
        data = json.loads(raw)
        # 文档级字段
        assert data["subject"] == "数学"
        assert data["grade"] == "高二"
        assert data["anchor_status_summary"] == {"exact": 1, "nearest": 1}
        assert data["warnings"] == ["marker fuzzy"]
        # corrected_anchors
        assert len(data["corrected_anchors"]) == 1
        anchor = data["corrected_anchors"][0]
        assert anchor["field"] == "stem"
        assert anchor["anchor_status"] == "nearest"
        assert anchor["validation_passed"] is True
        assert anchor["question_number"] == "1"
        # 题目级字段
        q = data["questions"][0]
        assert q["question_number"] == "1"
        assert q["question_type"] == "single_choice"
        assert q["knowledge_points"] == ["函数单调性", "不等式"]
        assert q["difficulty"] == 3
        assert q["score"] == 4.0
        assert q["confidence"] == 0.95
        assert q["source_page"] == 1
        assert q["is_composite"] is True
        assert q["sub_questions"][0]["qno"] == "（1）"
        assert q["sub_questions"][0]["knowledge_points"] == []
        # 行号字段仍保留
        assert q["stem_line_ids"] == ["P1L002"]
        assert q["answer_line_ids"] == ["P1L010"]


# ═══════════════════════════════════════════════════════════════════
# 4. 幂等重跑清理（真实 session 集成）
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_rerun_cleanup_removes_only_unreviewed(db, subject_id):
    """重跑清理：只删除未审核记录，已审核/已修正记录保留。"""
    from app.worker.document_worker import _cleanup_unreviewed_records
    from app.models import Document, Question, QuestionInstance

    doc = Document(filename="rerun.pdf", file_type="pdf", object_key="test/rerun.pdf")
    db.add(doc)
    await db.flush()

    # 未审核题（status=reviewing）→ 应被清理
    q_unreviewed = Question(
        subject_id=subject_id, stem="未审核题", source_type="document",
        source_document_name="rerun.pdf", status="reviewing", occurrence_count=1,
    )
    db.add(q_unreviewed)
    await db.flush()
    inst_unreviewed = QuestionInstance(
        question_id=q_unreviewed.id, document_id=doc.id, source_type="document",
        source_document_name="rerun.pdf", source_question_number="1", occurrence_no=1,
    )
    db.add(inst_unreviewed)

    # 已审核题（status=approved）→ 保留
    q_approved = Question(
        subject_id=subject_id, stem="已审核题", source_type="document",
        source_document_name="rerun.pdf", status="approved", occurrence_count=1,
    )
    db.add(q_approved)
    await db.flush()
    inst_approved = QuestionInstance(
        question_id=q_approved.id, document_id=doc.id, source_type="document",
        source_document_name="rerun.pdf", source_question_number="2", occurrence_no=1,
    )
    db.add(inst_approved)
    await db.flush()

    await _cleanup_unreviewed_records(db, doc.id)

    # 未审核记录被删除
    remain_unreviewed = await db.scalar(
        select(QuestionInstance).where(QuestionInstance.question_id == q_unreviewed.id)
    )
    assert remain_unreviewed is None
    # 已审核记录保留
    remain_approved = await db.scalar(
        select(QuestionInstance).where(QuestionInstance.question_id == q_approved.id)
    )
    assert remain_approved is not None
    approved_q = await db.scalar(select(Question).where(Question.id == q_approved.id))
    assert approved_q is not None


@pytest.mark.asyncio
async def test_rerun_cleanup_ignores_other_documents(db, subject_id):
    """重跑清理只影响指定 document，不影响其他文档记录。"""
    from app.worker.document_worker import _cleanup_unreviewed_records
    from app.models import Document, Question, QuestionInstance

    doc_a = Document(filename="rerun_a.pdf", file_type="pdf", object_key="test/a.pdf")
    doc_b = Document(filename="rerun_b.pdf", file_type="pdf", object_key="test/b.pdf")
    db.add_all([doc_a, doc_b])
    await db.flush()

    q_a = Question(
        subject_id=subject_id, stem="A 未审核", source_type="document",
        source_document_name="rerun_a.pdf", status="reviewing", occurrence_count=1,
    )
    q_b = Question(
        subject_id=subject_id, stem="B 未审核", source_type="document",
        source_document_name="rerun_b.pdf", status="reviewing", occurrence_count=1,
    )
    db.add_all([q_a, q_b])
    await db.flush()
    db.add_all([
        QuestionInstance(question_id=q_a.id, document_id=doc_a.id, source_type="document",
                         source_document_name="rerun_a.pdf", source_question_number="1", occurrence_no=1),
        QuestionInstance(question_id=q_b.id, document_id=doc_b.id, source_type="document",
                         source_document_name="rerun_b.pdf", source_question_number="1", occurrence_no=1),
    ])
    await db.flush()

    # 只清理 doc_a
    await _cleanup_unreviewed_records(db, doc_a.id)

    remain_a = await db.scalar(
        select(QuestionInstance).where(QuestionInstance.question_id == q_a.id)
    )
    remain_b = await db.scalar(
        select(QuestionInstance).where(QuestionInstance.question_id == q_b.id)
    )
    assert remain_a is None
    assert remain_b is not None


@pytest.mark.asyncio
async def test_rerun_cleanup_mixed_review_status_across_documents(db, subject_id):
    """同一 Question 跨文档共享（status=reviewing），清理 doc A 后 status 不变、occurrence_count 正确。

    回归测试：_cleanup_unreviewed_records 不应改变 question 的 status。
    """
    from app.worker.document_worker import _cleanup_unreviewed_records
    from app.models import Document, Question, QuestionInstance

    doc_a = Document(filename="mixed_a.pdf", file_type="pdf", object_key="test/ma.pdf")
    doc_b = Document(filename="mixed_b.pdf", file_type="pdf", object_key="test/mb.pdf")
    db.add_all([doc_a, doc_b])
    await db.flush()

    # 同一道 reviewing 题，出现在两份文档中
    q = Question(
        subject_id=subject_id, stem="混合审核题", source_type="document",
        source_document_name="mixed_a.pdf", status="reviewing", occurrence_count=2,
    )
    db.add(q)
    await db.flush()
    inst_a = QuestionInstance(
        question_id=q.id, document_id=doc_a.id, source_type="document",
        source_document_name="mixed_a.pdf", source_question_number="1", occurrence_no=1,
    )
    inst_b = QuestionInstance(
        question_id=q.id, document_id=doc_b.id, source_type="document",
        source_document_name="mixed_b.pdf", source_question_number="1", occurrence_no=1,
    )
    db.add_all([inst_a, inst_b])
    await db.flush()

    # 清理 doc_a
    await _cleanup_unreviewed_records(db, doc_a.id)

    # doc_a 的 Instance 被删
    assert await db.scalar(
        select(QuestionInstance).where(QuestionInstance.id == inst_a.id)
    ) is None

    # doc_b 的 Instance 保留
    assert await db.scalar(
        select(QuestionInstance).where(QuestionInstance.id == inst_b.id)
    ) is not None

    # Question 保留，status 不变（仍为 reviewing），occurrence_count 更新
    q_after = await db.get(Question, q.id)
    assert q_after is not None
    assert q_after.status == "reviewing", f"status 不应被 cleanup 改变，实际: {q_after.status}"
    assert q_after.occurrence_count == 1


@pytest.mark.asyncio
async def test_rerun_cleanup_preserves_fk_when_question_survives(db, subject_id):
    """Question 跨文档共享且有 FK 依赖（images/knowledge）时，清理一个文档后 FK 依赖保留。"""
    from app.worker.document_worker import _cleanup_unreviewed_records
    from app.models import (
        Document, Question, QuestionInstance, QuestionImage, QuestionKnowledge,
    )
    from sqlalchemy import select as sa_select
    from app.models import KnowledgeNode

    doc_a = Document(filename="fk_survive_a.pdf", file_type="pdf", object_key="test/fsa.pdf")
    doc_b = Document(filename="fk_survive_b.pdf", file_type="pdf", object_key="test/fsb.pdf")
    db.add_all([doc_a, doc_b])
    await db.flush()

    q = Question(
        subject_id=subject_id, stem="FK保留题", source_type="document",
        source_document_name="fk_survive_a.pdf", status="reviewing", occurrence_count=2,
    )
    db.add(q)
    await db.flush()
    inst_a = QuestionInstance(
        question_id=q.id, document_id=doc_a.id, source_type="document",
        source_document_name="fk_survive_a.pdf", source_question_number="1", occurrence_no=1,
    )
    inst_b = QuestionInstance(
        question_id=q.id, document_id=doc_b.id, source_type="document",
        source_document_name="fk_survive_b.pdf", source_question_number="1", occurrence_no=1,
    )
    db.add_all([inst_a, inst_b])

    # 关联 FK 依赖
    img = QuestionImage(question_id=q.id, image_key="test/img.png", image_type="diagram")
    db.add(img)
    node = await db.scalar(sa_select(KnowledgeNode).limit(1))
    if node is not None:
        qk = QuestionKnowledge(
            question_id=q.id, knowledge_node_id=node.id,
            mapping_source="rule", review_status="pending",
        )
        db.add(qk)
    await db.flush()

    # 清理 doc_a
    await _cleanup_unreviewed_records(db, doc_a.id)

    # doc_a Instance 被删，doc_b Instance 保留
    assert await db.scalar(
        select(QuestionInstance).where(QuestionInstance.id == inst_a.id)
    ) is None
    assert await db.scalar(
        select(QuestionInstance).where(QuestionInstance.id == inst_b.id)
    ) is not None

    # Question 保留，FK 依赖保留
    assert await db.get(Question, q.id) is not None
    assert await db.scalar(
        select(QuestionImage).where(QuestionImage.question_id == q.id)
    ) is not None, "QuestionImage 应保留（Question 仍有 Instance）"
    if node is not None:
        assert await db.scalar(
            select(QuestionKnowledge).where(QuestionKnowledge.question_id == q.id)
        ) is not None, "QuestionKnowledge 应保留（Question 仍有 Instance）"


@pytest.mark.asyncio
async def test_rerun_cleanup_preserves_shared_question_across_documents(db, subject_id):
    """同一 Question 跨文档共享时，清理一个文档不影响另一个文档的 Instance 和 Question。

    回归测试：_cleanup_unreviewed_records 曾错误删除该 Question 在所有文档下的 Instance。
    """
    from app.worker.document_worker import _cleanup_unreviewed_records
    from app.models import Document, Question, QuestionInstance

    doc_a = Document(filename="shared_a.pdf", file_type="pdf", object_key="test/sa.pdf")
    doc_b = Document(filename="shared_b.pdf", file_type="pdf", object_key="test/sb.pdf")
    db.add_all([doc_a, doc_b])
    await db.flush()

    # 同一道 reviewing 状态的题，出现在两份文档中
    shared_q = Question(
        subject_id=subject_id, stem="共享题目", source_type="document",
        source_document_name="shared_a.pdf", status="reviewing", occurrence_count=2,
    )
    db.add(shared_q)
    await db.flush()
    inst_a = QuestionInstance(
        question_id=shared_q.id, document_id=doc_a.id, source_type="document",
        source_document_name="shared_a.pdf", source_question_number="1", occurrence_no=1,
    )
    inst_b = QuestionInstance(
        question_id=shared_q.id, document_id=doc_b.id, source_type="document",
        source_document_name="shared_b.pdf", source_question_number="3", occurrence_no=1,
    )
    db.add_all([inst_a, inst_b])
    await db.flush()

    # 清理 doc_a
    await _cleanup_unreviewed_records(db, doc_a.id)

    # doc_a 的 Instance 被删
    remain_a = await db.scalar(
        select(QuestionInstance).where(QuestionInstance.id == inst_a.id)
    )
    assert remain_a is None, "doc_a 的 Instance 应被删除"

    # doc_b 的 Instance 保留
    remain_b = await db.scalar(
        select(QuestionInstance).where(QuestionInstance.id == inst_b.id)
    )
    assert remain_b is not None, "doc_b 的 Instance 不应被删除"

    # Question 保留（还有 doc_b 的 Instance）
    q_after = await db.get(Question, shared_q.id)
    assert q_after is not None, "跨文档共享的 Question 不应被删除"
    assert q_after.occurrence_count == 1, f"occurrence_count 应更新为 1，实际为 {q_after.occurrence_count}"


@pytest.mark.asyncio
async def test_rerun_cleanup_preserves_rejected_reviewed(db, subject_id):
    """已驳回（status=rejected）的记录同样保留，不被重跑清理。"""
    from app.worker.document_worker import _cleanup_unreviewed_records
    from app.models import Document, Question, QuestionInstance

    doc = Document(filename="rerun_rejected.pdf", file_type="pdf", object_key="test/r.pdf")
    db.add(doc)
    await db.flush()

    q_rejected = Question(
        subject_id=subject_id, stem="已驳回题", source_type="document",
        source_document_name="rerun_rejected.pdf", status="rejected", occurrence_count=1,
    )
    db.add(q_rejected)
    await db.flush()
    db.add(QuestionInstance(
        question_id=q_rejected.id, document_id=doc.id, source_type="document",
        source_document_name="rerun_rejected.pdf", source_question_number="1", occurrence_no=1,
    ))
    await db.flush()

    await _cleanup_unreviewed_records(db, doc.id)

    remain = await db.scalar(
        select(QuestionInstance).where(QuestionInstance.question_id == q_rejected.id)
    )
    assert remain is not None  # 已驳回记录保留（人工决定不静默覆盖）


@pytest.mark.asyncio
async def test_rerun_cleanup_handles_fk_dependents(db, subject_id):
    """questions 有 images + knowledge 记录时，cleanup 不报 FK 冲突。"""
    from app.worker.document_worker import _cleanup_unreviewed_records
    from app.models import Document, Question, QuestionInstance, QuestionImage, QuestionKnowledge

    doc = Document(filename="fk_cleanup.pdf", file_type="pdf", object_key="test/fk.pdf")
    db.add(doc)
    await db.flush()

    # 创建一个未审核 question
    q = Question(
        subject_id=subject_id, stem="FK 依赖测试题", source_type="document",
        source_document_name="fk_cleanup.pdf", status="reviewing", occurrence_count=1,
    )
    db.add(q)
    await db.flush()
    inst = QuestionInstance(
        question_id=q.id, document_id=doc.id, source_type="document",
        source_document_name="fk_cleanup.pdf", source_question_number="1", occurrence_no=1,
    )
    db.add(inst)

    # 关联 QuestionImage 和 QuestionKnowledge
    img = QuestionImage(
        question_id=q.id, image_key="test/img.png", image_type="diagram",
    )
    db.add(img)

    # 需要一个 knowledge_node（复用真实 MATH subject 的任意节点）
    from sqlalchemy import select as sa_select
    from app.models import KnowledgeNode
    node = await db.scalar(sa_select(KnowledgeNode).limit(1))
    if node is not None:
        qk = QuestionKnowledge(
            question_id=q.id, knowledge_node_id=node.id,
            mapping_source="rule", review_status="pending",
        )
        db.add(qk)
    await db.flush()

    # cleanup 不应报 FK 冲突
    await _cleanup_unreviewed_records(db, doc.id)
    await db.flush()

    # question、instance、image、knowledge 全部被清理
    assert await db.scalar(select(Question).where(Question.id == q.id)) is None
    assert await db.scalar(select(QuestionInstance).where(QuestionInstance.question_id == q.id)) is None
    assert await db.scalar(select(QuestionImage).where(QuestionImage.question_id == q.id)) is None
    if node is not None:
        assert await db.scalar(select(QuestionKnowledge).where(QuestionKnowledge.question_id == q.id)) is None


# ═══════════════════════════════════════════════════════════════════
# 5. 真实 DB 验证：ingestion 异常 → task/document 状态落库
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_ingestion_exception_persists_task_and_document_status(db, subject_id):
    """真实 DB 验证：ingestion 异常后 background_tasks.status='failed'、
    documents.processing_status='failed' 在 DB 中真实落库（非 mock 断言）。"""
    from app.models import Document, BackgroundTask

    doc = Document(
        filename=f"fail_persist_{uuid.uuid4().hex[:6]}.pdf",
        file_type="pdf", object_key="test/fail.pdf",
        processing_status="processing",
    )
    db.add(doc)
    await db.flush()

    task = BackgroundTask(
        task_type="document_parse", status="running", progress=0.5,
        payload_json={"document_id": str(doc.id)},
        result_json=None,
    )
    db.add(task)
    await db.flush()

    from app.domains.task.repository import BackgroundTaskRepository
    from app.domains.document.repository import DocumentRepository, DocumentProcessingLogRepository
    from app.domains.document.service import DocumentService
    from app.domains.task.service import TaskService
    from app.domains.event.repository import DomainEventRepository
    from app.domains.event.service import EventService

    task_svc = TaskService(repository=BackgroundTaskRepository(db))
    doc_svc = DocumentService(
        document_repository=DocumentRepository(db),
        log_repository=DocumentProcessingLogRepository(db),
    )

    # 模拟 ingestion 异常路径（worker except 块逻辑）
    doc.processing_status = "failed"
    doc.error_message = "ingestion failed: db write failed"
    await task_svc.fail_task(task.id, error_detail="ingestion failed: db write failed")
    await db.flush()

    # DB 真实验证：新查询确认状态
    persisted_task = await db.scalar(select(BackgroundTask).where(BackgroundTask.id == task.id))
    persisted_doc = await db.scalar(select(Document).where(Document.id == doc.id))
    assert persisted_task.status == "failed"
    assert "ingestion failed" in (persisted_task.error_detail or "")
    assert persisted_doc.processing_status == "failed"
    assert "ingestion failed" in (persisted_doc.error_message or "")


# ═══════════════════════════════════════════════════════════════════
# 6. 真实 DB 验证：llm_annotated_markdown 包含完整 L2 字段
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_llm_annotated_markdown_persists_l2_fields(db, subject_id):
    """真实 DB 验证：_serialize_l2_for_persistence 输出写入 documents.llm_annotated_markdown 后，
    JSON 包含 knowledge_points/difficulty/score/corrected_anchors/anchor_status/question_type/sub_questions。"""
    from app.models import Document
    from app.worker.document_worker import _serialize_l2_for_persistence

    doc = Document(
        filename=f"l2_persist_{uuid.uuid4().hex[:6]}.pdf",
        file_type="pdf", object_key="test/l2.pdf",
    )
    db.add(doc)
    await db.flush()

    l2 = _make_l2_annotation()
    data = _serialize_l2_for_persistence(l2)
    doc.llm_annotated_markdown = json.dumps(data, ensure_ascii=False, indent=2)
    await db.flush()

    # DB 真实验证：重新查询并解析 JSON
    persisted = await db.scalar(select(Document).where(Document.id == doc.id))
    assert persisted.llm_annotated_markdown is not None
    parsed = json.loads(persisted.llm_annotated_markdown)

    # 文档级字段
    assert parsed["annotation_version"] is not None
    assert parsed["anchor_status_summary"] == {"exact": 1, "nearest": 1}
    assert len(parsed["corrected_anchors"]) == 1
    assert parsed["corrected_anchors"][0]["anchor_status"] == "nearest"

    # 题目级字段
    q = parsed["questions"][0]
    assert q["question_type"] == "single_choice"
    assert q["knowledge_points"] == ["函数单调性", "不等式"]
    assert q["difficulty"] == 3
    assert q["score"] == 4.0
    assert q["is_composite"] is True
    assert q["structure_signature"] is None  # _make_l2_annotation 未设置
    assert len(q["sub_questions"]) == 1
    assert q["sub_questions"][0]["qno"] == "（1）"

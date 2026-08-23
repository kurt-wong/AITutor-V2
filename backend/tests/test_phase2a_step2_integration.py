"""
Phase 2A Step 2 集成测试 — 审核决定写回 DB。

覆盖（docs_archive/2026-08-24/PHASE_2A_EXECUTION_PLAN.md Step 2 必须新增测试）：
1. 审核通过后 questions.status = 'approved'（DB 真实变化）
2. 审核驳回后 questions.status = 'rejected'（DB 真实变化）
3. review_overrides 的 stem/options/answer/explanation 写回对应 Question（DB 真实变化）
4. 题目定位使用 question_instances(document_id, source_question_number)，同题号不同文档不串题
5. task.result_json 与 questions 表同时更新（application 层编排）

真实 PostgreSQL 集成测试：每个测试函数在独立事务中执行并回滚（不污染 DB）。
完整流程测试（test_review_end_to_end_writes_db）使用独立连接并显式清理。
"""
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.application.services import DocumentApplicationService
from app.core.config import settings
from app.domains.document.repository import (
    DocumentProcessingLogRepository,
    DocumentRepository,
)
from app.domains.document.service import DocumentService
from app.domains.event.repository import DomainEventRepository
from app.domains.event.service import EventService
from app.domains.question.repository import QuestionRepository
from app.domains.question.service import QuestionService
from app.domains.task.repository import BackgroundTaskRepository
from app.domains.task.service import TaskService
from app.infrastructure.storage import MinIOStorage
from app.models import (
    Document,
    Question,
    QuestionInstance,
    Subject,
    BackgroundTask,
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
    subj = Subject(code=f"test_step2_{uuid.uuid4().hex[:8]}", name="测试学科_Step2")
    db.add(subj)
    await db.flush()
    return subj.id


async def _make_doc_and_question(db, subject_id, *, filename: str, qno: str, stem: str):
    """构造 document + question + instance 三元组，返回 (doc, q)。"""
    doc = Document(
        filename=filename,
        file_type="pdf",
        object_key=f"test/{filename}",
    )
    db.add(doc)
    await db.flush()

    q = Question(
        subject_id=subject_id,
        stem=stem,
        source_type="document",
        source_document_name=filename,
        status="reviewing",
        occurrence_count=1,
        answer="原答案",
        explanation="原详解",
        options=[{"label": "A", "text": "原选项A"}],
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
    await db.flush()
    return doc, q


# ═══════════════════════════════════════════════════════════════════
# 1. Repository 定位（document_id + source_question_number）
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_repository_locates_question_by_document_and_number(db, subject_id):
    """同题号出现在两个不同文档时，只能定位到指定文档的那道题。"""
    doc_a, q_a = await _make_doc_and_question(
        db, subject_id, filename=f"doc_a_{uuid.uuid4().hex[:6]}.pdf",
        qno="7", stem="文档A的第7题",
    )
    doc_b, q_b = await _make_doc_and_question(
        db, subject_id, filename=f"doc_b_{uuid.uuid4().hex[:6]}.pdf",
        qno="7", stem="文档B的第7题",
    )

    repo = QuestionRepository(db)
    found_a = await repo.find_by_document_and_question_number(doc_a.id, "7")
    found_b = await repo.find_by_document_and_question_number(doc_b.id, "7")

    assert found_a is not None and found_a.id == q_a.id
    assert found_b is not None and found_b.id == q_b.id
    assert found_a.id != found_b.id


@pytest.mark.asyncio
async def test_repository_returns_none_when_number_missing(db, subject_id):
    """指定文档中不存在该题号时返回 None，不允许回退到任意同号题。"""
    doc, _ = await _make_doc_and_question(
        db, subject_id, filename=f"doc_c_{uuid.uuid4().hex[:6]}.pdf",
        qno="1", stem="只存在第1题",
    )
    repo = QuestionRepository(db)
    assert await repo.find_by_document_and_question_number(doc.id, "99") is None


# ═══════════════════════════════════════════════════════════════════
# 2. Service 层：apply_review 写回 status + overrides
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_apply_review_approved_updates_db_status(db, subject_id):
    """审核通过后 questions.status 在 DB 中真实变为 approved。"""
    doc, q = await _make_doc_and_question(
        db, subject_id, filename=f"doc_ok_{uuid.uuid4().hex[:6]}.pdf",
        qno="1", stem="审核通过题",
    )
    svc = QuestionService(repository=QuestionRepository(db))

    updated = await svc.apply_review(q.id, status="approved")

    assert updated is not None and updated.status == "approved"
    # 重新从 DB 查询，确认不是仅内存对象变化
    persisted = await db.scalar(
        select(Question).where(Question.id == q.id)
    )
    assert persisted is not None
    assert persisted.status == "approved"


@pytest.mark.asyncio
async def test_apply_review_rejected_updates_db_status(db, subject_id):
    """审核驳回后 questions.status 在 DB 中真实变为 rejected。"""
    doc, q = await _make_doc_and_question(
        db, subject_id, filename=f"doc_no_{uuid.uuid4().hex[:6]}.pdf",
        qno="2", stem="审核驳回题",
    )
    svc = QuestionService(repository=QuestionRepository(db))

    updated = await svc.apply_review(q.id, status="rejected")

    persisted = await db.scalar(
        select(Question).where(Question.id == q.id)
    )
    assert persisted is not None
    assert persisted.status == "rejected"


@pytest.mark.asyncio
async def test_apply_review_overrides_write_back_fields(db, subject_id):
    """review_overrides 的 stem/options/answer/explanation 写回对应 Question。"""
    doc, q = await _make_doc_and_question(
        db, subject_id, filename=f"doc_ov_{uuid.uuid4().hex[:6]}.pdf",
        qno="3", stem="原题干",
    )
    svc = QuestionService(repository=QuestionRepository(db))

    await svc.apply_review(
        q.id,
        status="approved",
        overrides={
            "stem": "修正后的题干",
            "options": [{"label": "A", "text": "修正选项A"}, {"label": "B", "text": "修正选项B"}],
            "answer": "B",
            "explanation": "修正详解",
        },
    )

    persisted = await db.scalar(
        select(Question).where(Question.id == q.id)
    )
    assert persisted.stem == "修正后的题干"
    assert persisted.answer == "B"
    assert persisted.explanation == "修正详解"
    assert persisted.options == [
        {"label": "A", "text": "修正选项A"},
        {"label": "B", "text": "修正选项B"},
    ]


@pytest.mark.asyncio
async def test_apply_review_partial_overrides_only_changes_given_fields(db, subject_id):
    """只提供部分 override 时，未提供的字段保持不变。"""
    doc, q = await _make_doc_and_question(
        db, subject_id, filename=f"doc_po_{uuid.uuid4().hex[:6]}.pdf",
        qno="4", stem="原题干",
    )
    svc = QuestionService(repository=QuestionRepository(db))

    await svc.apply_review(q.id, status="approved", overrides={"answer": "C"})

    persisted = await db.scalar(
        select(Question).where(Question.id == q.id)
    )
    assert persisted.answer == "C"
    assert persisted.stem == "原题干"          # 未覆盖
    assert persisted.explanation == "原详解"    # 未覆盖


@pytest.mark.asyncio
async def test_apply_review_unknown_question_returns_none(db, subject_id):
    """不存在的 question_id 返回 None，不静默写库。"""
    svc = QuestionService(repository=QuestionRepository(db))
    assert await svc.apply_review(uuid.uuid4(), status="approved") is None


# ═══════════════════════════════════════════════════════════════════
# 3. Application 层编排：task.result_json 与 questions 同时更新
# ═══════════════════════════════════════════════════════════════════


def _build_application_service(db, question_service):
    """构造真实 repository 的 DocumentApplicationService（question_service 可 mock）。"""
    return DocumentApplicationService(
        document_service=DocumentService(
            document_repository=DocumentRepository(db),
            log_repository=DocumentProcessingLogRepository(db),
        ),
        task_service=TaskService(repository=BackgroundTaskRepository(db)),
        event_service=EventService(repository=DomainEventRepository(db)),
        storage=MinIOStorage(),
        question_service=question_service,
    )


@pytest.mark.asyncio
async def test_update_document_review_updates_task_result_and_question(db, subject_id):
    """update_document_review 同时更新 task.result_json 与 questions 表。"""
    from unittest.mock import AsyncMock

    doc, q = await _make_doc_and_question(
        db, subject_id, filename=f"doc_e2e_{uuid.uuid4().hex[:6]}.pdf",
        qno="5", stem="端到端审核题",
    )
    task = BackgroundTask(
        task_type="document_parse",
        status="succeeded",
        progress=1,
        payload_json={"document_id": str(doc.id)},
        result_json={
            "status": "succeeded",
            "questions": [{"question_number": "5"}],
        },
    )
    db.add(task)
    await db.flush()

    fake_question_service = AsyncMock()
    fake_question_service.find_by_document_and_question_number.return_value = q
    fake_question_service.apply_review.return_value = q

    svc = _build_application_service(db, fake_question_service)
    returned_task, error_code = await svc.update_document_review(
        doc.id,
        question_number="5",
        status="approved",
        comment="人工确认正确",
        overrides={"stem": "人工修正题干", "answer": "B"},
    )

    assert error_code is None
    assert returned_task is not None
    # task.result_json 更新
    assert returned_task.result_json["review_decisions"]["5"]["status"] == "approved"
    assert returned_task.result_json["review_decisions"]["5"]["comment"] == "人工确认正确"
    assert returned_task.result_json["review_overrides"]["5"]["stem"] == "人工修正题干"
    # questions 表同步更新（mock 收到正确参数）
    fake_question_service.find_by_document_and_question_number.assert_awaited_once_with(
        doc.id, "5"
    )
    fake_question_service.apply_review.assert_awaited_once_with(
        q.id, status="approved", overrides={"stem": "人工修正题干", "answer": "B"}
    )


@pytest.mark.asyncio
async def test_update_document_review_question_id_priority(db, subject_id):
    """显式传入 question_id 时优先使用，不走题号匹配。"""
    from unittest.mock import AsyncMock

    doc, q = await _make_doc_and_question(
        db, subject_id, filename=f"doc_prio_{uuid.uuid4().hex[:6]}.pdf",
        qno="6", stem="携带 question_id 的审核",
    )
    task = BackgroundTask(
        task_type="document_parse",
        status="succeeded",
        progress=1,
        payload_json={"document_id": str(doc.id)},
        result_json={
            "status": "succeeded",
            "questions": [{"question_number": "6", "id": str(q.id)}],
        },
    )
    db.add(task)
    await db.flush()

    fake_question_service = AsyncMock()
    fake_question_service.get_question.return_value = q
    fake_question_service.apply_review.return_value = q

    svc = _build_application_service(db, fake_question_service)
    returned_task, error_code = await svc.update_document_review(
        doc.id,
        question_number="6",
        status="rejected",
        question_id=q.id,
    )

    assert error_code is None
    fake_question_service.get_question.assert_awaited_once_with(q.id)
    fake_question_service.find_by_document_and_question_number.assert_not_awaited()
    fake_question_service.apply_review.assert_awaited_once_with(
        q.id, status="rejected", overrides=None
    )
    assert returned_task.result_json["review_decisions"]["6"]["status"] == "rejected"
    assert returned_task.result_json["review_decisions"]["6"]["question_id"] == str(q.id)


@pytest.mark.asyncio
async def test_update_document_review_question_not_found(db, subject_id):
    """定位不到题目时返回 QUESTION_NOT_FOUND，task.result_json 不落库。"""
    from unittest.mock import AsyncMock

    doc, _ = await _make_doc_and_question(
        db, subject_id, filename=f"doc_nf_{uuid.uuid4().hex[:6]}.pdf",
        qno="8", stem="定位不到",
    )
    task = BackgroundTask(
        task_type="document_parse",
        status="succeeded",
        progress=1,
        payload_json={"document_id": str(doc.id)},
        result_json={"status": "succeeded", "questions": []},
    )
    db.add(task)
    await db.flush()

    fake_question_service = AsyncMock()
    fake_question_service.find_by_document_and_question_number.return_value = None

    svc = _build_application_service(db, fake_question_service)
    returned_task, error_code = await svc.update_document_review(
        doc.id,
        question_number="99",
        status="approved",
    )

    assert returned_task is None
    assert error_code == "QUESTION_NOT_FOUND"
    # result_json 未被写入（task 对象在事务内仍是原始状态）
    assert "review_decisions" not in (task.result_json or {})


# ═══════════════════════════════════════════════════════════════════
# 4. 端到端：真实 DB 上完整执行 update_document_review 后 SELECT 验证
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_review_end_to_end_writes_db(async_engine):
    """完整流程：审核通过 + 修正题干后，DB SELECT 返回修正内容和 approved 状态。"""
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    subject_code = f"test_step2_e2e_{uuid.uuid4().hex[:8]}"
    filename = f"e2e_{uuid.uuid4().hex[:6]}.pdf"
    try:
        async with session_factory() as session:
            subj = Subject(code=subject_code, name="测试学科_Step2_E2E")
            session.add(subj)
            await session.flush()

            doc, q = await _make_doc_and_question(
                session, subj.id, filename=filename,
                qno="10", stem="E2E 原题干",
            )
            task = BackgroundTask(
                task_type="document_parse",
                status="succeeded",
                progress=1,
                payload_json={"document_id": str(doc.id)},
                result_json={"status": "succeeded", "questions": [{"question_number": "10"}]},
            )
            session.add(task)
            await session.flush()

            real_question_service = QuestionService(repository=QuestionRepository(session))
            svc = _build_application_service(session, real_question_service)

            returned_task, error_code = await svc.update_document_review(
                doc.id,
                question_number="10",
                status="approved",
                overrides={"stem": "E2E 修正后的题干", "answer": "D"},
            )
            assert error_code is None
            await session.commit()

        # 新连接 SELECT 验证：status 和内容真实落库
        async with session_factory() as session:
            # questions 表验证：status + overrides 写回
            row = await session.execute(
                select(Question)
                .join(QuestionInstance, QuestionInstance.question_id == Question.id)
                .where(QuestionInstance.document_id == doc.id)
                .where(QuestionInstance.source_question_number == "10")
            )
            persisted = row.scalar_one_or_none()
            assert persisted is not None
            assert persisted.status == "approved"
            assert persisted.stem == "E2E 修正后的题干"
            assert persisted.answer == "D"

            # task.result_json 同步验证：review_decisions + review_overrides 真实落库
            task_row = await session.execute(
                select(BackgroundTask).where(BackgroundTask.id == task.id)
            )
            persisted_task = task_row.scalar_one_or_none()
            assert persisted_task is not None
            decisions = persisted_task.result_json.get("review_decisions", {})
            assert decisions["10"]["status"] == "approved"
            overrides = persisted_task.result_json.get("review_overrides", {})
            assert overrides["10"]["stem"] == "E2E 修正后的题干"
            assert overrides["10"]["answer"] == "D"
    finally:
        # 清理测试数据
        async with session_factory() as session:
            await session.execute(
                QuestionInstance.__table__.delete().where(
                    QuestionInstance.document_id.in_(
                        select(Document.id).where(Document.filename == filename)
                    )
                )
            )
            await session.execute(
                Question.__table__.delete().where(Question.source_document_name == filename)
            )
            await session.execute(
                Document.__table__.delete().where(Document.filename == filename)
            )
            await session.execute(
                BackgroundTask.__table__.delete().where(
                    BackgroundTask.payload_json["document_id"].astext == str(doc.id)
                )
            )
            await session.execute(
                Subject.__table__.delete().where(Subject.code == subject_code)
            )
            await session.commit()
        await engine.dispose()

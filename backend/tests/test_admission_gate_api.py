"""Admission Gate 候选 API 集成测试。

覆盖：
1. GET /question-candidates — 列表查询
2. POST /question-candidates/{id}/approve — 审核通过（含 content_hash 去重）
3. POST /question-candidates/{id}/reject — 拒绝删除
4. GET /admission-metrics — 门禁指标
"""

import pytest
import pytest_asyncio
from uuid import uuid4

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from app.core.config import settings
from app.main import app
from app.core.database import get_db_session
from app.models import Document, Question, Subject, QuestionType
from app.models.tables import QuestionCandidate


# ═══════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════


@pytest_asyncio.fixture
async def client_and_db():
    """创建共享事件循环的 httpx AsyncClient + DB session。

    关键：session、override、client 必须在同一事件循环中创建，
    否则 asyncpg 会报 "attached to a different loop" 错误。
    每个测试使用独立的 engine/connection/transaction 以确保隔离。
    """
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.connect() as conn:
        async with conn.begin() as transaction:
            session = AsyncSession(bind=conn, expire_on_commit=False)

            async def _override():
                yield session

            app.dependency_overrides[get_db_session] = _override
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as c:
                yield c, session
            app.dependency_overrides.clear()
            # 强制回滚
            try:
                await transaction.rollback()
            except Exception:
                pass
    await engine.dispose()


# ═══════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════


async def _ensure_subject_and_type(session: AsyncSession):
    """确保 subject 和 question_type 存在。"""
    result = await session.execute(
        select(Subject).where(Subject.code == "math").limit(1)
    )
    subject = result.scalar_one_or_none()
    if not subject:
        subject = Subject(name="数学", code="math")
        session.add(subject)
        await session.flush()

    result = await session.execute(
        select(QuestionType).where(QuestionType.code == "single_choice").limit(1)
    )
    qt = result.scalar_one_or_none()
    if not qt:
        qt = QuestionType(
            code="single_choice",
            name="单选题",
            subject_id=subject.id,
        )
        session.add(qt)
        await session.flush()

    return subject, qt


async def _create_document(session: AsyncSession) -> Document:
    """创建测试文档。"""
    doc = Document(
        filename="test_api.pdf",
        file_type="pdf",
        object_key="test/api",
        subject="数学",
        grade="高一",
        processing_status="processing",
    )
    session.add(doc)
    await session.flush()
    return doc


async def _create_candidate(
    session: AsyncSession,
    *,
    subject: Subject,
    question_type: QuestionType,
    document: Document,
    stem: str = "下列哪个选项正确？",
    answer: str = "A",
    gate_decision: str = "review",
    content_hash: str | None = None,
) -> QuestionCandidate:
    """创建测试候选题目。"""
    # 使用 uuid4 生成唯一 content_hash 避免约束冲突
    hash_val = content_hash or f"hash_{uuid4().hex[:12]}"
    candidate = QuestionCandidate(
        subject_id=subject.id,
        question_type_id=question_type.id,
        grade="高一",
        stem=stem,
        answer=answer,
        options=[
            {"label": "A", "text": "选项A"},
            {"label": "B", "text": "选项B"},
            {"label": "C", "text": "选项C"},
            {"label": "D", "text": "选项D"},
        ],
        source_type="document",
        source_document_name="test_api.pdf",
        confidence=0.8,
        content_hash=hash_val,
        gate_decision=gate_decision,
        gate_reason="R06_answer_provenance_trusted",
        document_id=document.id,
    )
    session.add(candidate)
    await session.flush()
    return candidate


# ═══════════════════════════════════════════════════════════════════
# 测试用例
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_list_candidates_empty(client_and_db):
    """空列表返回正确结构。"""
    client, session = client_and_db
    resp = await client.get("/api/admin/question-candidates")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "items" in data
    assert "total" in data
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_candidates_with_data(client_and_db):
    """有数据时正确返回。"""
    client, session = client_and_db
    subject, qt = await _ensure_subject_and_type(session)
    doc = await _create_document(session)
    await _create_candidate(session, subject=subject, question_type=qt, document=doc, stem="题目一")
    await _create_candidate(
        session, subject=subject, question_type=qt, document=doc,
        stem="题目二", gate_decision="reject",
    )

    resp = await client.get("/api/admin/question-candidates")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] == 2


@pytest.mark.asyncio
async def test_list_candidates_filter_by_decision(client_and_db):
    """按 gate_decision 过滤。"""
    client, session = client_and_db
    subject, qt = await _ensure_subject_and_type(session)
    doc = await _create_document(session)
    await _create_candidate(session, subject=subject, question_type=qt, document=doc, gate_decision="review")
    await _create_candidate(session, subject=subject, question_type=qt, document=doc, gate_decision="reject")

    resp = await client.get("/api/admin/question-candidates", params={"gate_decision": "review"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["gate_decision"] == "review"


@pytest.mark.asyncio
async def test_approve_candidate_creates_question(client_and_db):
    """审核通过：创建 Question + 删除 Candidate。"""
    client, session = client_and_db
    subject, qt = await _ensure_subject_and_type(session)
    doc = await _create_document(session)
    candidate = await _create_candidate(session, subject=subject, question_type=qt, document=doc)

    resp = await client.post(f"/api/admin/question-candidates/{candidate.id}/approve")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "question_id" in data
    assert data["status"] == "approved"

    # 验证 Candidate 已删除
    c = await session.get(QuestionCandidate, candidate.id)
    assert c is None


@pytest.mark.asyncio
async def test_approve_candidate_not_found(client_and_db):
    """不存在的 ID 返回 404。"""
    client, _ = client_and_db
    fake_id = uuid4()
    resp = await client.post(f"/api/admin/question-candidates/{fake_id}/approve")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_approve_candidate_content_hash_conflict(client_and_db):
    """content_hash 已存在于 questions 表 → 409 CONFLICT。"""
    client, session = client_and_db
    subject, qt = await _ensure_subject_and_type(session)
    doc = await _create_document(session)

    # 先创建一个已存在的 Question（相同 content_hash）
    existing_q = Question(
        subject_id=subject.id,
        question_type_id=qt.id,
        grade="高一",
        stem="已存在的题目",
        answer="A",
        content_hash="hash_conflict_001",
        source_type="document",
        source_document_name="existing.pdf",
        status="approved",
    )
    session.add(existing_q)
    await session.flush()

    candidate = await _create_candidate(
        session, subject=subject, question_type=qt, document=doc,
        content_hash="hash_conflict_001",
    )

    resp = await client.post(f"/api/admin/question-candidates/{candidate.id}/approve")
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "CONFLICT"


@pytest.mark.asyncio
async def test_reject_candidate_deletes(client_and_db):
    """拒绝：删除 Candidate。"""
    client, session = client_and_db
    subject, qt = await _ensure_subject_and_type(session)
    doc = await _create_document(session)
    candidate = await _create_candidate(session, subject=subject, question_type=qt, document=doc)

    resp = await client.post(f"/api/admin/question-candidates/{candidate.id}/reject")
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "rejected"

    # 验证 Candidate 已删除
    c = await session.get(QuestionCandidate, candidate.id)
    assert c is None


@pytest.mark.asyncio
async def test_reject_candidate_not_found(client_and_db):
    """拒绝不存在的 ID 返回 404。"""
    client, _ = client_and_db
    fake_id = uuid4()
    resp = await client.post(f"/api/admin/question-candidates/{fake_id}/reject")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_admission_metrics(client_and_db):
    """门禁指标返回正确计数。"""
    client, session = client_and_db
    subject, qt = await _ensure_subject_and_type(session)
    doc = await _create_document(session)

    await _create_candidate(session, subject=subject, question_type=qt, document=doc, gate_decision="review")
    await _create_candidate(session, subject=subject, question_type=qt, document=doc, gate_decision="review")
    await _create_candidate(session, subject=subject, question_type=qt, document=doc, gate_decision="reject")

    resp = await client.get("/api/admin/admission-metrics")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "questions" in data
    assert "candidates" in data
    assert data["candidates"]["review"] >= 2
    assert data["candidates"]["reject"] >= 1

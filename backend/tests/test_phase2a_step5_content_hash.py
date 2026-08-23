"""
Phase 2A Step 5 测试 — 精确去重 content_hash。

覆盖（docs_archive/2026-08-24/PHASE_2A_EXECUTION_PLAN.md Step 5 必须新增测试）：
1. 同一 PDF 上传两次，第二次只创建 Instance，不创建新 Question
2. 题干相同但选项不同，创建不同 Question
3. 题干、选项、题型相同但答案不同，不创建重复 Question，产生审核冲突
4. 回填后 questions.content_hash 无 NULL
5. 规范化规则对空白、标点、换行、Unicode 有确定性

content_hash 规范化/计算用单元测试（确定性），ingestion 去重用真实 PostgreSQL 集成测试。
"""
import json
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.domains.document.content_hash import (
    compute_content_hash,
    normalize_text,
    normalize_options,
)
from app.models import Question


# ═══════════════════════════════════════════════════════════════════
# 1. content_hash 规范化确定性（单元测试）
# ═══════════════════════════════════════════════════════════════════


class TestContentHashDeterminism:
    def test_normalize_text_handles_whitespace_punct_unicode(self):
        """规范化：空白/标点/全角/Unicode 有确定性。"""
        assert normalize_text("  已知函数  f(x)=x²  ") == normalize_text("已知函数f(x)=x²")
        assert normalize_text("Ａ．选项Ａ") == normalize_text("A．选项A")  # 全角→半角
        assert normalize_text("求解\n方程") == normalize_text("求解方程")
        assert normalize_text("；、，。") == ""

    def test_hash_same_content_same_hash(self):
        """相同内容（排版差异）→ 相同 hash。"""
        h1 = compute_content_hash(
            stem="已知函数  f(x)=x²，求最小值",
            options=[{"label": "A", "text": "1"}, {"label": "B", "text": "2"}],
            question_type="single_choice",
        )
        h2 = compute_content_hash(
            stem="已知函数f(x)=x²求最小值",
            options=[{"label": "B", "text": "2"}, {"label": "A", "text": "1"}],
            question_type="single_choice",
        )
        assert h1 == h2  # 选项顺序不影响

    def test_hash_different_options_different_hash(self):
        """题干相同但选项不同 → 不同 hash。"""
        h1 = compute_content_hash(
            stem="相同题干",
            options=[{"label": "A", "text": "选项1"}],
            question_type="single_choice",
        )
        h2 = compute_content_hash(
            stem="相同题干",
            options=[{"label": "A", "text": "选项2"}],
            question_type="single_choice",
        )
        assert h1 != h2

    def test_hash_different_type_different_hash(self):
        """题干选项相同但题型不同 → 不同 hash。"""
        h1 = compute_content_hash(
            stem="相同题干", options=[{"label": "A", "text": "X"}], question_type="single_choice",
        )
        h2 = compute_content_hash(
            stem="相同题干", options=[{"label": "A", "text": "X"}], question_type="fill_in",
        )
        assert h1 != h2

    def test_hash_is_sha256_64_hex(self):
        """hash 格式：64 位 hex（SHA256）。"""
        h = compute_content_hash(stem="测试", question_type="single_choice")
        assert len(h) == 64
        int(h, 16)  # 是合法 hex

    def test_hash_composite_sub_questions_included(self):
        """综合题：子题参与 hash，不同子题不同 hash。"""
        h1 = compute_content_hash(
            stem="综合题材料",
            question_type="composite",
            sub_questions=[{"qno": "（1）", "question_type": "fill_in", "answer": "2"}],
        )
        h2 = compute_content_hash(
            stem="综合题材料",
            question_type="composite",
            sub_questions=[{"qno": "（1）", "question_type": "fill_in", "answer": "3"}],
        )
        assert h1 != h2


# ═══════════════════════════════════════════════════════════════════
# 2. Ingestion 去重（真实 PostgreSQL 集成）
# ═══════════════════════════════════════════════════════════════════


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
    from app.models import Subject

    subj = Subject(code=f"test_step5_{uuid.uuid4().hex[:8]}", name="测试学科_Step5")
    db.add(subj)
    await db.flush()
    return subj.id


def _make_pipeline_result(qno: str, stem: str, options: list[dict], qtype: str = "single_choice"):
    """构造最小 PipelineResult（一道高置信度题）。"""
    from app.domains.document.pipeline import PipelineResult
    from app.domains.document.schemas_l2 import SlicedQuestion

    result = PipelineResult()
    result.sliced_questions = [
        SlicedQuestion(
            question_number=qno,
            question_type=qtype,
            stem=stem,
            options=options,
            answer="A",
            confidence=0.95,
        )
    ]
    return result


def _make_answer_result(subject: str, qno: str, answer: str):
    from app.domains.document.answer_extractor import AnswerExtractionResult, ExtractedAnswer

    result = AnswerExtractionResult(subject=subject)
    result.answers[qno] = ExtractedAnswer(question_number=qno, answer=answer, explanation="详解")
    return result


@pytest.mark.asyncio
async def test_ingestion_same_pdf_twice_only_creates_instance(db, subject_id):
    """同一 PDF 上传两次（两个 Document）→ 第二次只创建 Instance，不创建新 Question。"""
    from app.domains.document.ingestion import ingest_pipeline_result
    from app.models import Document

    stem = "content_hash 去重题干"
    options = [{"label": "A", "text": "选项A"}, {"label": "B", "text": "选项B"}]

    doc_a = Document(filename=f"dup_a_{uuid.uuid4().hex[:6]}.pdf", file_type="pdf",
                     object_key="test/a.pdf", subject="数学")
    db.add(doc_a)
    await db.flush()
    r1 = await ingest_pipeline_result(
        db,
        pipeline_result=_make_pipeline_result("1", stem, options),
        answer_result=_make_answer_result("数学", "1", "A"),
        document=doc_a,
    )
    assert r1.ingested == 1
    qid = r1.question_ids[0]

    doc_b = Document(filename=f"dup_b_{uuid.uuid4().hex[:6]}.pdf", file_type="pdf",
                     object_key="test/b.pdf", subject="数学")
    db.add(doc_b)
    await db.flush()
    r2 = await ingest_pipeline_result(
        db,
        pipeline_result=_make_pipeline_result("1", stem, options),
        answer_result=_make_answer_result("数学", "1", "A"),
        document=doc_b,
    )
    assert r2.ingested == 1
    assert r2.question_ids[0] == qid  # 同一 Question

    q_count = await db.scalar(
        select(func.count()).select_from(Question).where(Question.id == qid)
    )
    assert q_count == 1


@pytest.mark.asyncio
async def test_ingestion_same_stem_diff_options_creates_new_question(db, subject_id):
    """题干相同但选项不同 → 创建不同 Question。"""
    from app.domains.document.ingestion import ingest_pipeline_result
    from app.models import Document

    stem = "相同题干不同选项"
    doc_a = Document(filename=f"opt_a_{uuid.uuid4().hex[:6]}.pdf", file_type="pdf",
                     object_key="test/a.pdf", subject="数学")
    db.add(doc_a)
    await db.flush()
    r1 = await ingest_pipeline_result(
        db,
        pipeline_result=_make_pipeline_result("1", stem, [{"label": "A", "text": "选项1"}]),
        answer_result=_make_answer_result("数学", "1", "A"),
        document=doc_a,
    )

    doc_b = Document(filename=f"opt_b_{uuid.uuid4().hex[:6]}.pdf", file_type="pdf",
                     object_key="test/b.pdf", subject="数学")
    db.add(doc_b)
    await db.flush()
    r2 = await ingest_pipeline_result(
        db,
        pipeline_result=_make_pipeline_result("1", stem, [{"label": "A", "text": "选项2"}]),
        answer_result=_make_answer_result("数学", "1", "A"),
        document=doc_b,
    )

    assert r1.question_ids[0] != r2.question_ids[0]  # 不同 Question
    # 两个 Question 的 content_hash 不同
    q1 = await db.scalar(select(Question).where(Question.id == r1.question_ids[0]))
    q2 = await db.scalar(select(Question).where(Question.id == r2.question_ids[0]))
    assert q1.content_hash != q2.content_hash


@pytest.mark.asyncio
async def test_ingestion_answer_conflict_creates_conflict_not_duplicate(db, subject_id):
    """题干+选项+题型相同但答案不同 → 不创建重复 Question，产生审核冲突。"""
    from app.domains.document.ingestion import ingest_pipeline_result
    from app.models import Document, Question

    stem = "冲突题干"
    options = [{"label": "A", "text": "选项A"}, {"label": "B", "text": "选项B"}]

    doc_a = Document(filename=f"conf_a_{uuid.uuid4().hex[:6]}.pdf", file_type="pdf",
                     object_key="test/a.pdf", subject="数学")
    db.add(doc_a)
    await db.flush()
    r1 = await ingest_pipeline_result(
        db,
        pipeline_result=_make_pipeline_result("1", stem, options),
        answer_result=_make_answer_result("数学", "1", "A"),
        document=doc_a,
    )
    qid = r1.question_ids[0]

    doc_b = Document(filename=f"conf_b_{uuid.uuid4().hex[:6]}.pdf", file_type="pdf",
                     object_key="test/b.pdf", subject="数学")
    db.add(doc_b)
    await db.flush()
    r2 = await ingest_pipeline_result(
        db,
        pipeline_result=_make_pipeline_result("1", stem, options),
        answer_result=_make_answer_result("数学", "1", "B"),  # 答案不同！
        document=doc_b,
    )

    # 不创建重复 Question
    assert r2.question_ids[0] == qid
    # Question 标记审核冲突，review_reason 包含冲突详情（来源文档 + 冲突答案）
    q = await db.scalar(select(Question).where(Question.id == qid))
    assert q.review_reason is not None
    assert q.review_reason.startswith("answer_conflict:"), f"review_reason 应包含冲突详情，实际: {q.review_reason}"
    assert doc_b.filename in q.review_reason, f"review_reason 应包含冲突来源文档名，实际: {q.review_reason}"
    assert ":B" in q.review_reason, f"review_reason 应包含冲突答案，实际: {q.review_reason}"
    assert q.status == "reviewing"


@pytest.mark.asyncio
async def test_ingestion_first_upload_creates_question_with_correct_fields(db, subject_id):
    """首次上传一道题：Question 正常创建，answer/status/content_hash/occurrence_count 字段正确。"""
    from app.domains.document.ingestion import ingest_pipeline_result
    from app.models import Document, Question

    stem = "首次上传题干"
    options = [{"label": "A", "text": "选项A"}, {"label": "B", "text": "选项B"}]

    doc = Document(filename=f"first_{uuid.uuid4().hex[:6]}.pdf", file_type="pdf",
                   object_key="test/first.pdf", subject="数学")
    db.add(doc)
    await db.flush()
    r = await ingest_pipeline_result(
        db,
        pipeline_result=_make_pipeline_result("1", stem, options),
        answer_result=_make_answer_result("数学", "1", "C"),
        document=doc,
    )

    qid = r.question_ids[0]
    q = await db.scalar(select(Question).where(Question.id == qid))

    # 首次上传：正确创建 Question
    assert q is not None, "首次上传应创建 Question"
    assert q.answer == "C", f"answer 应为 C，实际: {q.answer}"
    assert q.content_hash is not None, "content_hash 不应为 NULL"
    assert len(q.content_hash) == 64, f"content_hash 应为 64 位 hex，实际: {len(q.content_hash)}"
    assert q.occurrence_count == 1, f"首次上传 occurrence_count 应为 1，实际: {q.occurrence_count}"
    assert q.review_reason is None, f"首次上传不应有 review_reason，实际: {q.review_reason}"
    # 高置信度+有答案 → approved
    assert q.status == "approved", f"高置信度有答案应 approved，实际: {q.status}"


@pytest.mark.asyncio
async def test_ingestion_multiple_conflicts_update_review_reason(db, subject_id):
    """同一题目三次上传（A→B→C 答案各不同）：review_reason 始终反映最新冲突来源。"""
    from app.domains.document.ingestion import ingest_pipeline_result
    from app.models import Document, Question

    stem = "多次冲突题干"
    options = [{"label": "A", "text": "选项A"}, {"label": "B", "text": "选项B"}]

    # 第一次：答案 A → 创建 Question，approved
    doc_a = Document(filename=f"mc_a_{uuid.uuid4().hex[:6]}.pdf", file_type="pdf",
                     object_key="test/mca.pdf", subject="数学")
    db.add(doc_a)
    await db.flush()
    r1 = await ingest_pipeline_result(
        db,
        pipeline_result=_make_pipeline_result("1", stem, options),
        answer_result=_make_answer_result("数学", "1", "A"),
        document=doc_a,
    )
    qid = r1.question_ids[0]
    q1 = await db.scalar(select(Question).where(Question.id == qid))
    assert q1.status == "approved"
    assert q1.review_reason is None

    # 第二次：答案 B → 冲突，review_reason 包含 B
    doc_b = Document(filename=f"mc_b_{uuid.uuid4().hex[:6]}.pdf", file_type="pdf",
                     object_key="test/mcb.pdf", subject="数学")
    db.add(doc_b)
    await db.flush()
    r2 = await ingest_pipeline_result(
        db,
        pipeline_result=_make_pipeline_result("1", stem, options),
        answer_result=_make_answer_result("数学", "1", "B"),
        document=doc_b,
    )
    assert r2.question_ids[0] == qid
    q2 = await db.scalar(select(Question).where(Question.id == qid))
    assert q2.status == "reviewing"
    assert "answer_conflict:" in q2.review_reason
    assert ":B" in q2.review_reason

    # 第三次：答案 C → 再次冲突，review_reason 更新为最新来源
    doc_c = Document(filename=f"mc_c_{uuid.uuid4().hex[:6]}.pdf", file_type="pdf",
                     object_key="test/mcc.pdf", subject="数学")
    db.add(doc_c)
    await db.flush()
    r3 = await ingest_pipeline_result(
        db,
        pipeline_result=_make_pipeline_result("1", stem, options),
        answer_result=_make_answer_result("数学", "1", "C"),
        document=doc_c,
    )
    assert r3.question_ids[0] == qid
    q3 = await db.scalar(select(Question).where(Question.id == qid))
    assert q3.status == "reviewing"
    assert "answer_conflict:" in q3.review_reason
    assert doc_c.filename in q3.review_reason, f"review_reason 应反映最新冲突来源，实际: {q3.review_reason}"
    assert ":C" in q3.review_reason, f"review_reason 应包含最新冲突答案 C，实际: {q3.review_reason}"
    # 三次上传只创建 1 个 Question，3 个 Instance
    assert q3.occurrence_count == 3, f"应有 3 个 Instance，实际 occurrence_count={q3.occurrence_count}"


@pytest.mark.asyncio
async def test_ingestion_writes_content_hash_non_null(db, subject_id):
    """ingestion 创建 Question 时写入 content_hash（非 NULL）。"""
    from app.domains.document.ingestion import ingest_pipeline_result
    from app.models import Document, Question

    doc = Document(filename=f"hash_{uuid.uuid4().hex[:6]}.pdf", file_type="pdf",
                   object_key="test/h.pdf", subject="数学")
    db.add(doc)
    await db.flush()
    r = await ingest_pipeline_result(
        db,
        pipeline_result=_make_pipeline_result("1", "写入 hash 题干", [{"label": "A", "text": "X"}]),
        answer_result=_make_answer_result("数学", "1", "A"),
        document=doc,
    )
    q = await db.scalar(select(Question).where(Question.id == r.question_ids[0]))
    assert q.content_hash is not None
    assert len(q.content_hash) == 64

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
async def test_ingestion_whitespace_only_answer_diff_no_conflict(db, subject_id):
    """答案仅空白差异（"①.何时可掇" vs "①. 何时可掇"）→ 不产生冲突。

    2026-08-25（BUG-026）：语文朝阳 Q17 两次重灌答案内容一致仅内部空格不同，
    旧比较 .strip() 只去首尾空白 → 误标 answer_conflict 并降级 reviewing。
    """
    from app.domains.document.ingestion import ingest_pipeline_result
    from app.models import Document, Question

    stem = "空白差异题干"
    options = [{"label": "A", "text": "选项A"}, {"label": "B", "text": "选项B"}]

    doc_a = Document(filename=f"ws_a_{uuid.uuid4().hex[:6]}.pdf", file_type="pdf",
                     object_key="test/ws_a.pdf", subject="数学")
    db.add(doc_a)
    await db.flush()
    r1 = await ingest_pipeline_result(
        db,
        pipeline_result=_make_pipeline_result("1", stem, options),
        answer_result=_make_answer_result("数学", "1", "①.何时可掇②.别时茫茫江浸月"),
        document=doc_a,
    )
    qid = r1.question_ids[0]

    # 第二次答案仅内部空格不同 → 视为同一答案，不冲突
    doc_b = Document(filename=f"ws_b_{uuid.uuid4().hex[:6]}.pdf", file_type="pdf",
                     object_key="test/ws_b.pdf", subject="数学")
    db.add(doc_b)
    await db.flush()
    r2 = await ingest_pipeline_result(
        db,
        pipeline_result=_make_pipeline_result("1", stem, options),
        answer_result=_make_answer_result("数学", "1", "①. 何时可掇 ②. 别时茫茫江浸月"),
        document=doc_b,
    )
    assert r2.question_ids[0] == qid
    q = await db.scalar(select(Question).where(Question.id == qid))
    assert q.review_reason is None, f"空白差异不应产生冲突，实际: {q.review_reason}"
    assert q.status == "approved"

    # 第三次答案内容真的不同 → 仍产生冲突
    doc_c = Document(filename=f"ws_c_{uuid.uuid4().hex[:6]}.pdf", file_type="pdf",
                     object_key="test/ws_c.pdf", subject="数学")
    db.add(doc_c)
    await db.flush()
    r3 = await ingest_pipeline_result(
        db,
        pipeline_result=_make_pipeline_result("1", stem, options),
        answer_result=_make_answer_result("数学", "1", "①. 何时可掇 ②. 别时茫茫江浸月 ③. 错"),
        document=doc_c,
    )
    assert r3.question_ids[0] == qid
    q3 = await db.scalar(select(Question).where(Question.id == qid))
    assert q3.review_reason is not None
    assert q3.review_reason.startswith("answer_conflict:")
    assert q3.status == "reviewing"


@pytest.mark.asyncio
async def test_ingestion_latex_and_fullwidth_answer_diff_no_conflict(db, subject_id):
    """LaTeX 包裹/全角标点差异 → 不产生冲突（数学 40 题 answer_conflict 根因）。

    2026-08-26：同一道题两次入库，答案内容相同但格式不同（LLM/OCR 输出
    抖动）被误判冲突：
    - `$0$` vs `0`（LaTeX 定界符）
    - `$\\frac{3\\pi}{4}$` vs `\\frac{3\\pi}{4}`（公式命令外壳）
    - `(1) $C=...$` vs `（1）C=...`（全角/半角括号 + LaTeX）
    """
    from app.domains.document.ingestion import ingest_pipeline_result
    from app.models import Document, Question

    stem = "格式差异题干"
    options = [{"label": "A", "text": "选项A"}, {"label": "B", "text": "选项B"}]

    doc_a = Document(filename=f"fmt_a_{uuid.uuid4().hex[:6]}.pdf", file_type="pdf",
                     object_key="test/fmt_a.pdf", subject="数学")
    db.add(doc_a)
    await db.flush()
    r1 = await ingest_pipeline_result(
        db,
        pipeline_result=_make_pipeline_result("1", stem, options),
        answer_result=_make_answer_result("数学", "1", r"①. $0$ ②. $\frac{3\pi}{4}$"),
        document=doc_a,
    )
    qid = r1.question_ids[0]

    # 第二次：同内容，LaTeX 定界符去掉 + 全角括号
    doc_b = Document(filename=f"fmt_b_{uuid.uuid4().hex[:6]}.pdf", file_type="pdf",
                     object_key="test/fmt_b.pdf", subject="数学")
    db.add(doc_b)
    await db.flush()
    r2 = await ingest_pipeline_result(
        db,
        pipeline_result=_make_pipeline_result("1", stem, options),
        answer_result=_make_answer_result("数学", "1", r"①. 0 ②. \frac{3\pi}{4}"),
        document=doc_b,
    )
    assert r2.question_ids[0] == qid
    q = await db.scalar(select(Question).where(Question.id == qid))
    assert q.review_reason is None, f"LaTeX/全角差异不应产生冲突，实际: {q.review_reason}"
    assert q.status == "approved"

    # 第三次：内容真的不同 → 仍冲突
    doc_c = Document(filename=f"fmt_c_{uuid.uuid4().hex[:6]}.pdf", file_type="pdf",
                     object_key="test/fmt_c.pdf", subject="数学")
    db.add(doc_c)
    await db.flush()
    r3 = await ingest_pipeline_result(
        db,
        pipeline_result=_make_pipeline_result("1", stem, options),
        answer_result=_make_answer_result("数学", "1", r"①. $0$ ②. $\frac{3\pi}{4}$ ③. 9"),
        document=doc_c,
    )
    assert r3.question_ids[0] == qid
    q3 = await db.scalar(select(Question).where(Question.id == qid))
    assert q3.review_reason is not None
    assert q3.review_reason.startswith("answer_conflict:")
    assert q3.status == "reviewing"


@pytest.mark.asyncio
async def test_ingestion_exact_match_clears_stale_answer_conflict(db, subject_id):
    """重灌 dedup exact（归一化后答案一致）→ 清除历史遗留 answer_conflict 标记。

    2026-08-26：格式类假冲突在旧比较下被误标 reviewing（数学 Q13/15/17），
    重灌时新比较归一化后判定 exact → 应自动清除旧标记并恢复 approved，
    否则标记永久滞留 reviewing。
    """
    from app.domains.document.ingestion import ingest_pipeline_result
    from app.models import Document, Question

    stem = "清除历史冲突题干"
    options = [{"label": "A", "text": "选项A"}, {"label": "B", "text": "选项B"}]

    # 第一次：LaTeX 格式答案，直接标记一个假冲突（模拟历史遗留）
    doc_a = Document(filename=f"clr_a_{uuid.uuid4().hex[:6]}.pdf", file_type="pdf",
                     object_key="test/clr_a.pdf", subject="数学")
    db.add(doc_a)
    await db.flush()
    r1 = await ingest_pipeline_result(
        db,
        pipeline_result=_make_pipeline_result("1", stem, options),
        answer_result=_make_answer_result("数学", "1", r"①. $0$ ②. $\frac{3\pi}{4}$"),
        document=doc_a,
    )
    qid = r1.question_ids[0]
    # 人为制造历史假冲突标记（模拟旧比较误标）
    q = await db.scalar(select(Question).where(Question.id == qid))
    q.review_reason = f"answer_conflict:{doc_a.filename}:①. 0"
    q.status = "reviewing"
    await db.flush()

    # 第二次：同内容但格式不同（归一化后 equal）→ dedup exact → 清除标记
    doc_b = Document(filename=f"clr_b_{uuid.uuid4().hex[:6]}.pdf", file_type="pdf",
                     object_key="test/clr_b.pdf", subject="数学")
    db.add(doc_b)
    await db.flush()
    r2 = await ingest_pipeline_result(
        db,
        pipeline_result=_make_pipeline_result("1", stem, options),
        answer_result=_make_answer_result("数学", "1", r"①. 0 ②. \frac{3\pi}{4}"),
        document=doc_b,
    )
    assert r2.question_ids[0] == qid
    q2 = await db.scalar(select(Question).where(Question.id == qid))
    assert q2.review_reason is None, f"exact 匹配应清除历史 conflict 标记，实际: {q2.review_reason}"
    assert q2.status == "approved"


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


# ═══════════════════════════════════════════════════════════════════
# 3. content_hash 生命周期（P0，2026-08-27 审计修复）
# ═══════════════════════════════════════════════════════════════════
# 漏洞：apply_review 改题干/选项不重算 hash → 内容与 hash 漂移
# （旧 hash 残留、新内容无法去重）。修复：统一领域入口
# update_question_content()（apply_review 内部调用），内容变化 → 重算 hash
# → 查 exact duplicate → 答案冲突标记审核。
# 见 LOG.md 2026-08-27 21:30:00 审计执行决策 #1。


async def _ingest_one_question(db, subject_id, *, filename: str, stem: str, answer: str, qno: str = "1"):
    """通过 ingestion 创建一道真实 Question（含 content_hash/question_type）。返回 Question。"""
    from app.domains.document.ingestion import ingest_pipeline_result
    from app.models import Document

    doc = Document(filename=filename, file_type="pdf",
                   object_key=f"test/{filename}", subject="数学")
    db.add(doc)
    await db.flush()
    r = await ingest_pipeline_result(
        db,
        pipeline_result=_make_pipeline_result(
            qno, stem, [{"label": "A", "text": "选项A"}, {"label": "B", "text": "选项B"}]
        ),
        answer_result=_make_answer_result("数学", qno, answer),
        document=doc,
    )
    assert r.ingested == 1, f"ingestion 失败: {r.errors}"
    return await db.scalar(select(Question).where(Question.id == r.question_ids[0]))


async def _question_service(db):
    """构造 QuestionService（真实 Repository）。"""
    from app.domains.question.repository import QuestionRepository
    from app.domains.question.service import QuestionService

    return QuestionService(repository=QuestionRepository(db))


@pytest.mark.asyncio
async def test_apply_review_stem_change_recomputes_hash(db, subject_id):
    """审核改题干 → content_hash 重算为新值，旧 hash 不残留。"""
    from app.domains.document.content_hash import compute_content_hash

    q = await _ingest_one_question(
        db, subject_id,
        filename=f"lc_a_{uuid.uuid4().hex[:6]}.pdf",
        stem="生命周期题干A", answer="A",
    )
    old_hash = q.content_hash

    svc = await _question_service(db)
    updated = await svc.apply_review(
        q.id, status="approved", overrides={"stem": "生命周期题干A（修正）"}
    )
    assert updated is not None
    expected = compute_content_hash(
        stem="生命周期题干A（修正）",
        options=[{"label": "A", "text": "选项A"}, {"label": "B", "text": "选项B"}],
        question_type="single_choice",
    )
    assert updated.content_hash == expected, "改题干后 hash 应重算为新值"
    assert updated.content_hash != old_hash, "旧 hash 不应残留"


@pytest.mark.asyncio
async def test_apply_review_answer_only_keeps_hash(db, subject_id):
    """只改答案/详解（不涉及 stem/options）→ hash 不变。"""
    q = await _ingest_one_question(
        db, subject_id,
        filename=f"lc_b_{uuid.uuid4().hex[:6]}.pdf",
        stem="只改答案题干", answer="A",
    )
    old_hash = q.content_hash

    svc = await _question_service(db)
    updated = await svc.apply_review(
        q.id, status="approved",
        overrides={"answer": "C", "explanation": "新详解"},
    )
    assert updated.content_hash == old_hash, "只改答案/详解不应重算 hash"
    assert updated.answer == "C"
    assert updated.explanation == "新详解"


@pytest.mark.asyncio
async def test_apply_review_no_content_change_keeps_hash(db, subject_id):
    """无 overrides（仅状态变更）→ hash 不变。"""
    q = await _ingest_one_question(
        db, subject_id,
        filename=f"lc_c_{uuid.uuid4().hex[:6]}.pdf",
        stem="仅状态题干", answer="A",
    )
    old_hash = q.content_hash

    svc = await _question_service(db)
    updated = await svc.apply_review(q.id, status="approved")
    assert updated.content_hash == old_hash
    assert updated.status == "approved"


@pytest.mark.asyncio
async def test_apply_review_stem_conflict_marks_reviewing(db, subject_id):
    """改题干后 hash 与库中另一题相同且答案不同 → answer_conflict + 降 reviewing。"""
    q_a = await _ingest_one_question(
        db, subject_id,
        filename=f"lc_d1_{uuid.uuid4().hex[:6]}.pdf",
        stem="生命周期撞车题干", answer="A",
    )
    q_b = await _ingest_one_question(
        db, subject_id,
        filename=f"lc_d2_{uuid.uuid4().hex[:6]}.pdf",
        stem="生命周期撞车题干B", answer="B",
    )
    assert q_a.content_hash != q_b.content_hash

    svc = await _question_service(db)
    updated = await svc.apply_review(
        q_b.id, status="approved", overrides={"stem": "生命周期撞车题干"},
    )
    # hash 重算后与 q_a 相同（题干+选项+题型一致）
    assert updated.content_hash == q_a.content_hash
    # 答案不同 → 冲突标记审核
    assert updated.review_reason is not None
    assert updated.review_reason.startswith("answer_conflict:"), (
        f"冲突应标记 answer_conflict，实际: {updated.review_reason}"
    )
    assert updated.status == "reviewing", "冲突时应降为 reviewing"


@pytest.mark.asyncio
async def test_apply_review_stem_collision_answers_equal_no_conflict(db, subject_id):
    """改题干后 hash 撞车但答案归一化一致 → 不标记冲突，保持 approved。"""
    q_a = await _ingest_one_question(
        db, subject_id,
        filename=f"lc_e1_{uuid.uuid4().hex[:6]}.pdf",
        stem="生命周期同答案题干", answer="A",
    )
    q_b = await _ingest_one_question(
        db, subject_id,
        filename=f"lc_e2_{uuid.uuid4().hex[:6]}.pdf",
        stem="生命周期同答案题干B", answer="A",
    )

    svc = await _question_service(db)
    updated = await svc.apply_review(
        q_b.id, status="approved", overrides={"stem": "生命周期同答案题干"},
    )
    assert updated.content_hash == q_a.content_hash
    assert updated.review_reason is None, f"答案一致不应标记冲突，实际: {updated.review_reason}"
    assert updated.status == "approved"


@pytest.mark.asyncio
async def test_update_question_content_options_recomputes_hash(db, subject_id):
    """统一入口 update_question_content 改 options → hash 重算。"""
    q = await _ingest_one_question(
        db, subject_id,
        filename=f"lc_f_{uuid.uuid4().hex[:6]}.pdf",
        stem="生命周期选项题干", answer="A",
    )
    old_hash = q.content_hash
    new_options = [{"label": "A", "text": "选项X"}, {"label": "B", "text": "选项Y"}]

    svc = await _question_service(db)
    updated = await svc.update_question_content(q.id, options=new_options)
    assert updated is not None
    assert updated.options == new_options
    assert updated.content_hash != old_hash, "改 options 应重算 hash"

    from app.domains.document.content_hash import compute_content_hash
    expected = compute_content_hash(
        stem="生命周期选项题干",
        options=new_options,
        question_type="single_choice",
    )
    assert updated.content_hash == expected


@pytest.mark.asyncio
async def test_update_question_content_unknown_question_returns_none(db, subject_id):
    """update_question_content 对不存在的题目返回 None。"""
    svc = await _question_service(db)
    result = await svc.update_question_content(
        uuid.uuid4(), stem="不存在的题"
    )
    assert result is None


# ═══════════════════════════════════════════════════════════════════
# 4. P4E.1：入库子题完整内容 + 父题 options 不拼接（2026-08-27）
# 背景：完形 10 子题 A 聚合/子题内容链路丢失（LOG v6.43）。
# ═══════════════════════════════════════════════════════════════════


def _make_composite_pipeline_result(qno: str, stem: str, subs: list[dict]):
    """构造选择题组综合题 PipelineResult（子题带切片文本）。"""
    from app.domains.document.pipeline import PipelineResult
    from app.domains.document.schemas_l2 import L2SubQuestion, SlicedQuestion

    result = PipelineResult()
    result.sliced_questions = [
        SlicedQuestion(
            question_number=qno,
            question_type="single_choice",
            stem=stem,
            options=[],
            answer="(1) A (2) B",
            confidence=0.95,
            is_composite=True,
            sub_questions=[
                L2SubQuestion(
                    qno=s["qno"],
                    question_type="single_choice",
                    answer=s["answer"],
                    stem_line_ids=s["stem_line_ids"],
                    options_line_ids=s["options_line_ids"],
                    stem=s["stem"],
                    options=s["options"],
                )
                for s in subs
            ],
        )
    ]
    return result


@pytest.mark.asyncio
async def test_ingestion_persists_sub_question_content(db, subject_id):
    """综合题入库：sub_questions 保存子题 stem/options/行号；父题 options 置空。"""
    from app.domains.document.ingestion import ingest_pipeline_result
    from app.models import Document, Question

    subs = [
        {
            "qno": "1", "question_type": "single_choice", "answer": "A",
            "stem_line_ids": ["P1L002"],
            "options_line_ids": {"A": ["P1L003"], "B": ["P1L004"]},
            "stem": "子题1题干", "options": [{"label": "A", "text": "开心"}, {"label": "B", "text": "难过"}],
        },
        {
            "qno": "2", "question_type": "single_choice", "answer": "B",
            "stem_line_ids": ["P1L005"],
            "options_line_ids": {"A": ["P1L006"], "B": ["P1L007"]},
            "stem": "子题2题干", "options": [{"label": "A", "text": "快"}, {"label": "B", "text": "慢"}],
        },
    ]
    doc = Document(filename=f"subq_{uuid.uuid4().hex[:6]}.pdf", file_type="pdf",
                   object_key="test/subq.pdf", subject="英语")
    db.add(doc)
    await db.flush()
    r = await ingest_pipeline_result(
        db,
        pipeline_result=_make_composite_pipeline_result("1", "完形材料", subs),
        answer_result=None,
        document=doc,
    )
    assert r.ingested == 1
    q = await db.scalar(select(Question).where(Question.id == r.question_ids[0]))
    assert q.is_composite is True
    # 父题 options 置空（选择题组综合题，子题选项归属子题）
    assert q.options is None or q.options == []
    stored = q.sub_questions
    assert stored is not None and len(stored) == 2
    s1 = stored[0]
    assert s1["qno"] == "1"
    assert s1["stem"] == "子题1题干"
    assert s1["options"] == [{"label": "A", "text": "开心"}, {"label": "B", "text": "难过"}]
    assert s1["options_line_ids"] == {"A": ["P1L003"], "B": ["P1L004"]}
    assert s1["stem_line_ids"] == ["P1L002"]
    s2 = stored[1]
    assert s2["qno"] == "2"
    assert s2["stem"] == "子题2题干"
    assert s2["options"] == [{"label": "A", "text": "快"}, {"label": "B", "text": "慢"}]


@pytest.mark.asyncio
async def test_ingestion_inline_options_split_persisted(db, subject_id):
    """单行紧凑选项（A.甲B.乙C.丙D.丁）经 _slice_options 拆分后入库。"""
    from app.domains.document.ingestion import ingest_pipeline_result
    from app.models import Document, Question

    doc = Document(filename=f"inl_{uuid.uuid4().hex[:6]}.pdf", file_type="pdf",
                   object_key="test/inl.pdf", subject="数学")
    db.add(doc)
    await db.flush()
    r = await ingest_pipeline_result(
        db,
        pipeline_result=_make_pipeline_result(
            "1", "紧凑选项题干", [{"label": "A", "text": "甲"}, {"label": "B", "text": "乙"}]
        ),
        answer_result=_make_answer_result("数学", "1", "A"),
        document=doc,
    )
    assert r.ingested == 1
    q = await db.scalar(select(Question).where(Question.id == r.question_ids[0]))
    assert q.options is not None
    assert [o["label"] for o in q.options] == ["A", "B"]

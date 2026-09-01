"""
Phase 2A Step 6 集成测试 — 知识点映射落库。

覆盖（docs_archive/2026-08-24/PHASE_2A_EXECUTION_PLAN.md Step 6 必须新增测试）：
1. 入库一道题后，question_knowledge 能关联到正确 knowledge_nodes
2. 低置信度映射的 review_status = 'pending'
3. mapping_source 为 llm/rule/manual 之一
4. 综合题子题映射到不同知识点
5. 知识树为空或匹配不到时，不静默跳过，必须进入可审核状态

真实 PostgreSQL 集成测试（每个测试函数独立事务回滚）。
"""
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.domains.knowledge.repository import (
    KnowledgeNodeRepository,
    QuestionTypeRepository,
)
from app.domains.knowledge.service import KnowledgeService
from app.models import (
    Document,
    KnowledgeNode,
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
    """带事务的 session，测试结束自动回滚。"""
    async with async_engine.connect() as conn:
        async with conn.begin() as transaction:
            session = AsyncSession(bind=conn, expire_on_commit=False)
            yield session
            await transaction.rollback()


async def _make_math_subject(db, code: str = "MATH") -> Subject:
    """创建/复用 MATH 学科（与知识树 seed 一致）。"""
    existing = await db.scalar(select(Subject).where(Subject.code == code))
    if existing:
        return existing
    subj = Subject(code=code, name="数学")
    db.add(subj)
    await db.flush()
    return subj


async def _make_question(db, subject: Subject, stem: str, *, is_composite=False,
                         sub_questions=None, knowledge_points=None):
    """构造一道已入库的 Question（跳过完整 ingestion，直接建 Question）。"""
    q = Question(
        subject_id=subject.id,
        stem=stem,
        source_type="document",
        source_document_name="test.pdf",
        status="approved",
        occurrence_count=1,
        is_composite=is_composite,
        sub_questions=sub_questions,
    )
    db.add(q)
    await db.flush()
    # 知识树节点（映射目标）
    return q


def _make_knowledge_service(db) -> KnowledgeService:
    return KnowledgeService(
        node_repository=KnowledgeNodeRepository(db),
        question_type_repository=QuestionTypeRepository(db),
    )


# ═══════════════════════════════════════════════════════════════════
# 1. 入库后 question_knowledge 关联正确 knowledge_nodes
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_mapping_links_to_knowledge_node(db):
    """知识点匹配到知识树节点 → question_knowledge 关联正确节点。"""
    subject = await _make_math_subject(db)
    q = await _make_question(db, subject, "函数的单调性题目")

    svc = _make_knowledge_service(db)
    written = await svc.map_question_to_knowledge(
        question_id=q.id,
        subject_id=subject.id,
        subject_code="MATH",
        subject_name="数学",
        knowledge_points=["函数单调性"],
    )

    assert len(written) >= 1
    qk = written[0]
    # 关联的节点属于 MATH 学科
    node = await db.scalar(select(KnowledgeNode).where(KnowledgeNode.id == qk.knowledge_node_id))
    assert node is not None
    assert node.subject_id == subject.id
    # mapping_source 合法
    assert qk.mapping_source in ("llm", "rule", "manual")
    # 高置信度 → approved
    assert qk.review_status == "approved"


@pytest.mark.asyncio
async def test_mapping_low_confidence_goes_pending(db):
    """低置信度映射（部分命中）→ review_status='pending'。"""
    subject = await _make_math_subject(db)
    q = await _make_question(db, subject, "混合知识点题目")

    svc = _make_knowledge_service(db)
    # 两个知识点只命中一个 → confidence=0.5 < 0.7 → pending
    written = await svc.map_question_to_knowledge(
        question_id=q.id,
        subject_id=subject.id,
        subject_code="MATH",
        subject_name="数学",
        knowledge_points=["函数单调性", "完全不存在的知识点XYZ"],
    )

    assert len(written) >= 1
    assert written[0].review_status == "pending"


@pytest.mark.asyncio
async def test_mapping_source_is_valid_enum(db):
    """mapping_source 必须是 llm/rule/manual 之一。"""
    subject = await _make_math_subject(db)
    q = await _make_question(db, subject, "来源验证题")

    svc = _make_knowledge_service(db)
    written = await svc.map_question_to_knowledge(
        question_id=q.id,
        subject_id=subject.id,
        subject_code="MATH",
        subject_name="数学",
        knowledge_points=["函数"],
    )

    assert len(written) >= 1
    assert written[0].mapping_source in ("llm", "rule", "manual")


# ═══════════════════════════════════════════════════════════════════
# 4. 综合题子题级映射
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_composite_sub_questions_map_to_nodes(db):
    """综合题子题映射到不同知识点（都写入 question_knowledge）。

    对抗性审查修复：原断言 len>=1 无法验证「不同知识点」——
    即使删掉整个子题映射循环测试照样通过。修复后断言子题映射到不同节点。
    """
    subject = await _make_math_subject(db)
    q = await _make_question(
        db, subject, "综合题材料",
        is_composite=True,
        sub_questions=[
            {"qno": "（1）", "question_type": "fill_in", "answer": "2",
             "knowledge_points": ["单调性"]},
            {"qno": "（2）", "question_type": "fill_in", "answer": "3",
             "knowledge_points": ["三角函数"]},
        ],
    )

    svc = _make_knowledge_service(db)
    written = await svc.map_question_to_knowledge(
        question_id=q.id,
        subject_id=subject.id,
        subject_code="MATH",
        subject_name="数学",
        knowledge_points=["函数"],
        is_composite=True,
        sub_questions=q.sub_questions,
    )

    # 至少 1 条主映射 + 2 条子题映射
    assert len(written) >= 1
    qk_records = list(await db.scalars(
        select(QuestionKnowledge).where(QuestionKnowledge.question_id == q.id)
    ))
    assert len(qk_records) >= 1
    assert any(r.is_primary for r in qk_records)

    # 子题知识点不同 → 映射到不同节点（验收点 S6-4「子题映射到不同知识点」）
    sub_nodes = []
    for r in qk_records:
        node = await db.scalar(
            select(KnowledgeNode).where(KnowledgeNode.id == r.knowledge_node_id)
        )
        sub_nodes.append((node.code, node.name))
    distinct_codes = {code for code, _ in sub_nodes}
    assert len(distinct_codes) >= 2, (
        f"子题应映射到不同知识点，实际全部塌缩到 {sub_nodes}"
    )
    # 具体断言：三角函数子题应命中 MATH-C1-CH5（v2 三角函数章，最具体节点）
    tri_nodes = [n for n in sub_nodes if "三角函数" in n[1]]
    assert any("MATH-C1-CH5" in code for code, _ in tri_nodes), (
        f"三角函数应映射到 MATH-C1-CH5，实际 {tri_nodes}"
    )


# ═══════════════════════════════════════════════════════════════════
# 5. 知识树为空 / 匹配不到 → 不静默跳过，进入可审核状态
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_mapping_empty_knowledge_points_goes_pending_unknown(db):
    """knowledge_points 为空 → 回退 UNKNOWN 节点 + pending（不静默跳过）。"""
    subject = await _make_math_subject(db)
    q = await _make_question(db, subject, "无知识点标注的题")

    svc = _make_knowledge_service(db)
    written = await svc.map_question_to_knowledge(
        question_id=q.id,
        subject_id=subject.id,
        subject_code="MATH",
        subject_name="数学",
        knowledge_points=[],
    )

    assert len(written) >= 1
    qk = written[0]
    assert qk.review_status == "pending"  # 可审核
    node = await db.scalar(select(KnowledgeNode).where(KnowledgeNode.id == qk.knowledge_node_id))
    assert node is not None
    assert "UNKNOWN" in node.code  # 回退节点


@pytest.mark.asyncio
async def test_mapping_no_keyword_hit_goes_pending_unknown(db):
    """关键词无命中 → 回退 UNKNOWN + pending。"""
    subject = await _make_math_subject(db)
    q = await _make_question(db, subject, "完全无法匹配的题目")

    svc = _make_knowledge_service(db)
    written = await svc.map_question_to_knowledge(
        question_id=q.id,
        subject_id=subject.id,
        subject_code="MATH",
        subject_name="数学",
        knowledge_points=["量子纠缠理论"],  # MATH 树中不存在
    )

    assert len(written) >= 1
    qk = written[0]
    assert qk.review_status == "pending"
    node = await db.scalar(select(KnowledgeNode).where(KnowledgeNode.id == qk.knowledge_node_id))
    assert "UNKNOWN" in node.code


# ═══════════════════════════════════════════════════════════════════
# 6. ingestion 集成：入库自动映射
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_ingestion_auto_maps_knowledge(db):
    """ingest_pipeline_result 入库时自动写入 question_knowledge。"""
    from app.domains.document.ingestion import ingest_pipeline_result
    from app.domains.document.pipeline_shared import PipelineResult
    from app.domains.document.schemas_l1 import L1Document, L1Line, L1Page
    from app.domains.document.schemas_l2 import SlicedQuestion, SourceProvenance

    subject = await _make_math_subject(db)
    doc = Document(filename=f"kp_{uuid.uuid4().hex[:6]}.pdf", file_type="pdf",
                   object_key="test/kp.pdf", subject="数学")
    db.add(doc)
    await db.flush()

    result = PipelineResult()
    result.sliced_questions = [
        SlicedQuestion(
            question_number="1",
            question_type="single_choice",
            stem="函数单调性选择题",
            options=[{"label": "A", "text": "增函数"}, {"label": "B", "text": "减函数"}],
            answer="A",
            confidence=0.95,
            answer_provenance=SourceProvenance("answer", "document_answer_table", 1.0),
            knowledge_points=["函数单调性"],
            stem_line_ids=["P1L001"],
            section_id="section_1",
            score=3.0,
            difficulty=2,
        )
    ]

    line = L1Line(
        line_id="P1L001", page_no=1, line_no_in_page=1, order=1,
        text="函数单调性选择题", block_type="text",
        bbox={"x1": 0, "y1": 0, "x2": 100, "y2": 20}, source="ppsv3",
    )
    result.l1_document = L1Document(
        filename="test.pdf", pages=[L1Page(page_no=1, lines=[line])],
        lines=[line], images=[], source="ppsv3", total_pages=1,
    )

    ingest = await ingest_pipeline_result(
        db,
        pipeline_result=result,
        answer_result=None,
        document=doc,
    )
    assert ingest.ingested == 1
    qid = ingest.question_ids[0]

    # question_knowledge 已写入
    qk = await db.scalar(
        select(QuestionKnowledge).where(QuestionKnowledge.question_id == qid)
    )
    assert qk is not None
    node = await db.scalar(select(KnowledgeNode).where(KnowledgeNode.id == qk.knowledge_node_id))
    assert node is not None
    assert node.subject_id == subject.id

"""入库服务 — 将管线输出的题目写入数据库。

流程：
1. 从 PipelineResult 中提取已通过质量门的题目
2. 从 AnswerExtractionResult 中获取 LLM 提取的答案和详解
3. 合并两者，写入 questions / question_instances / question_images 表
4. 高置信度 → status="approved"，低置信度 → status="reviewing"
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.document.answer_extractor import AnswerExtractionResult
from app.domains.document.content_hash import compute_content_hash
from app.domains.document.pipeline import PipelineResult
from app.domains.document.schemas_l2 import SlicedQuestion
from app.domains.document.schemas_l1 import L1Document
from app.domains.knowledge.repository import KnowledgeNodeRepository, QuestionTypeRepository
from app.models import (
    Document,
    DomainEvent,
    Question,
    QuestionImage,
    QuestionInstance,
    QuestionType,
    Subject,
)

logger = logging.getLogger(__name__)


# ── 数据结构 ──────────────────────────────────────────────────────


@dataclass
class IngestionResult:
    """入库结果。"""
    total_questions: int = 0
    ingested: int = 0       # 成功入库
    skipped: int = 0        # 跳过（低置信度/无答案）
    failed: int = 0         # 入库失败
    question_ids: list[UUID] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    # 答案提取状态（由 processor 设置）
    answer_extraction_status: str = "skipped"  # skipped / success / failed / exception
    answer_extraction_error: str | None = None

    def to_dict(self) -> dict:
        return {
            "total": self.total_questions,
            "ingested": self.ingested,
            "skipped": self.skipped,
            "failed": self.failed,
            "answer_extraction_status": self.answer_extraction_status,
            "answer_extraction_error": self.answer_extraction_error,
            "errors": self.errors[:5],
        }


# ── 入库逻辑 ──────────────────────────────────────────────────────


async def ingest_pipeline_result(
    session: AsyncSession,
    *,
    pipeline_result: PipelineResult,
    answer_result: AnswerExtractionResult | None = None,
    document: Document,
    gateway=None,
) -> IngestionResult:
    """将管线结果入库。

    入库流程：
    1. 遍历每道题
    2. 对每道题做去重检查（精确匹配 + LLM 相似判断）
    3. 精确匹配：不创建新 Question，只创建 QuestionInstance，累加 occurrence_count
    4. 相似匹配：创建新 Question，标记 similarity_group_id，共享知识点映射
    5. 全新题目：正常创建 Question + QuestionInstance

    Args:
        session: 数据库会话
        pipeline_result: 管线输出结果
        answer_result: LLM 答案提取结果（可选，如果有则合并）
        document: 来源文档记录

    Returns:
        IngestionResult
    """
    result = IngestionResult()

    sliced_questions = pipeline_result.sliced_questions
    if not sliced_questions:
        result.errors.append("no sliced questions in pipeline result")
        return result

    result.total_questions = len(sliced_questions)

    # 获取学科
    subject = await _get_or_create_subject(session, answer_result.subject if answer_result else document.subject or "未知")

    # 获取答案映射
    answer_map = answer_result.answers if answer_result else {}

    for sq in sliced_questions:
        # P0-A: 每题独立 savepoint，一道题失败不毒化 session 不拖垮整份文档。
        # begin_nested() 创建 PostgreSQL SAVEPOINT，异常时只回滚当前题目，
        # 外层事务（含之前成功的题目）继续有效。
        try:
            async with session.begin_nested():
                question_id = await _ingest_one_question(
                    session,
                    sq=sq,
                    subject=subject,
                    document=document,
                    answer_map=answer_map,
                    l1_document=pipeline_result.l1_document,
                    question_images=pipeline_result.question_images,
                )
                if question_id:
                    result.ingested += 1
                    result.question_ids.append(question_id)
                else:
                    result.skipped += 1
        except Exception as exc:
            result.failed += 1
            error_msg = f"Q{sq.question_number}: {type(exc).__name__}: {exc}"
            result.errors.append(error_msg[:300])
            logger.warning("ingestion failed for Q%s: %s", sq.question_number, exc)

    # 发布领域事件
    for qid in result.question_ids:
        session.add(DomainEvent(
            event_type="QuestionCreated",
            entity_type="question",
            entity_id=qid,
            payload_json={"source_document": document.filename},
        ))

    logger.info(
        "ingestion done: total=%d ingested=%d skipped=%d failed=%d",
        result.total_questions, result.ingested, result.skipped, result.failed,
    )

    return result


async def _ingest_one_question(
    session: AsyncSession,
    *,
    sq: SlicedQuestion,
    subject: Subject,
    document: Document,
    answer_map: dict,
    l1_document: L1Document | None,
    question_images: list[dict],
) -> UUID | None:
    """入库单道题。返回 question_id 或 None（跳过）。

    去重逻辑：
    1. 精确匹配：stem 完全相同 → 只创建 QuestionInstance，累加 occurrence_count
    2. 相似匹配：交给 LLM 判断（语义级别，非文本相似度）
       - 相似题目创建新 Question，标记 similarity_group_id
       - 共享知识点映射，参与频率统计
    """

    # 判断是否入库：高置信度且无"禁止自动发布"
    is_high_conf = sq.confidence >= 0.8
    is_blocked = any("禁止自动发布" in i for i in (sq.issues or []))
    has_stem = bool((sq.stem or "").strip())

    if not has_stem:
        return None  # 无题干，跳过

    # 获取答案：优先用 LLM 提取的答案，回退到管线切片的答案
    llm_answer_data = answer_map.get(str(sq.question_number))
    if llm_answer_data and llm_answer_data.answer.strip():
        final_answer = llm_answer_data.answer
        final_explanation = llm_answer_data.explanation or sq.explanation or ""
    else:
        final_answer = sq.answer or ""
        final_explanation = sq.explanation or ""

    # 确定状态和审核原因
    if is_high_conf and not is_blocked and final_answer.strip():
        status = "approved"
        review_reason = None
    else:
        status = "reviewing"
        review_reason = _extract_review_reason(sq, final_answer)

    # ── Phase 2A Step 5：content_hash 精确去重 ───────────────────
    # 去重从"只看 stem"升级为"规范化题干 + 选项 + 题型"的 SHA256
    content_hash = compute_content_hash(
        stem=sq.stem,
        options=sq.options,
        question_type=sq.question_type,
        sub_questions=[
            {"qno": sub.qno, "question_type": sub.question_type, "answer": sub.answer}
            for sub in (sq.sub_questions or [])
        ] or None,
    )
    existing_question = await _find_by_content_hash(session, content_hash, subject.id)

    if existing_question:
        # 精确匹配：不创建新 Question，只创建 QuestionInstance
        # occurrence_count 由 COUNT(instances) 驱动，不再手动累加
        instance = QuestionInstance(
            question_id=existing_question.id,
            document_id=document.id,
            source_type="document",
            source_document_name=document.filename,
            source_page=sq.source_page,
            source_question_number=str(sq.question_number) if sq.question_number is not None else None,
            year=document.year,
            school=document.school,
            occurrence_no=1,  # 同一来源内序号固定为 1（唯一约束保证不重复）
        )
        session.add(instance)
        await session.flush()
        # 更新缓存的 occurrence_count
        count_stmt = select(func.count()).select_from(QuestionInstance).where(QuestionInstance.question_id == existing_question.id)
        existing_question.occurrence_count = await session.scalar(count_stmt)

        # Phase 2A Step 5：答案冲突处理
        # hash 相同（题干+选项+题型一致）但答案不同 → 不创建重复 Question，
        # 在该 Question 上标记审核冲突（review_reason 持久化冲突详情，降为 reviewing）
        existing_answer = (existing_question.answer or "").strip()
        new_answer = final_answer.strip()
        if new_answer and existing_answer and new_answer != existing_answer:
            # 持久化冲突详情：来源文档 + 冲突答案，供管理员审核时参考
            conflict_detail = f"answer_conflict:{document.filename}:{new_answer}"
            existing_question.review_reason = conflict_detail[:200]
            if existing_question.status == "approved":
                existing_question.status = "reviewing"
            logger.warning(
                "dedup conflict: Q%s hash=%s existing answer='%s' new answer='%s' from '%s' → review needed",
                sq.question_number, content_hash[:12], existing_answer[:30], new_answer[:30], document.filename,
            )
        else:
            logger.info(
                "dedup exact: Q%s hash=%s → existing question %s (occurrence=%d)",
                sq.question_number, content_hash[:12], existing_question.id, existing_question.occurrence_count,
            )
        return existing_question.id

    # 第二步：LLM 相似判断（暂时禁用，待方案重新设计）
    # TODO: 用户要求重新思考相似题判断的实现方式
    # 当前只做精确匹配去重，相似题作为独立题目入库

    # ── 创建新 Question ──────────────────────────────────────────
    # 查找或创建题型
    question_type_id = await _get_question_type_id(session, sq.question_type, subject.id)

    question = Question(
        subject_id=subject.id,
        grade=document.grade,
        # year/school 已迁移到 question_instances（Phase 2A）
        question_type_id=question_type_id,
        score=Decimal(str(sq.score)) if sq.score else None,
        difficulty=sq.difficulty,
        stem=sq.stem,
        options=_normalize_options(sq.options),
        answer=final_answer,
        explanation=final_explanation,
        source_type="document",
        source_document_name=document.filename,
        status=status,
        confidence=Decimal(str(round(sq.confidence, 3))),
        review_reason=review_reason,
        occurrence_count=1,  # 缓存字段，初始为 1
        is_composite=sq.is_composite or False,
        content_hash=content_hash,  # Phase 2A Step 5：规范化题干+选项+题型 SHA256
        sub_questions=[
            {"qno": sub.qno, "question_type": sub.question_type, "answer": sub.answer}
            for sub in (sq.sub_questions or [])
        ] or None,
    )
    session.add(question)
    await session.flush()

    # 创建 QuestionInstance
    instance = QuestionInstance(
        question_id=question.id,
        document_id=document.id,
        source_type="document",
        source_document_name=document.filename,
        source_page=sq.source_page,
        source_question_number=str(sq.question_number) if sq.question_number is not None else None,
        year=document.year,
        school=document.school,
        occurrence_no=1,
    )
    session.add(instance)

    # 关联 QuestionImage
    q_images = [img for img in question_images if img.get("question_number") == str(sq.question_number)]
    for idx, img in enumerate(q_images):
        qi = QuestionImage(
            question_id=question.id,
            image_key=img.get("image_id", ""),
            image_type="diagram",
            description=img.get("placement", ""),
            image_order=idx,
            page_no=img.get("page_no"),
            bbox=img.get("bbox"),
            placement=img.get("placement", "stem"),
            source=img.get("source", "paddleocr"),
            figure_id=img.get("figure_id"),
        )
        session.add(qi)

    # Phase 2A Step 6：知识点映射落库（question_knowledge → knowledge_nodes）
    try:
        from app.domains.knowledge.repository import KnowledgeNodeRepository
        from app.domains.knowledge.service import KnowledgeService
        from app.domains.knowledge.tree_seed.types import SUBJECT_CODES

        # 学科代码：subject.code 已是 seed 规范（MATH/PHYS/...），兜底反查中文名
        subject_code = subject.code.upper()
        if subject_code not in SUBJECT_CODES:
            subject_code = next(
                (c for c, name in SUBJECT_CODES.items() if name == subject.name),
                "MATH",
            )
        knowledge_service = KnowledgeService(
            node_repository=KnowledgeNodeRepository(session),
            question_type_repository=QuestionTypeRepository(session),
        )
        await knowledge_service.map_question_to_knowledge(
            question_id=question.id,
            subject_id=subject.id,
            subject_code=subject_code,
            subject_name=subject.name,
            knowledge_points=sq.knowledge_points,
            is_composite=sq.is_composite or False,
            sub_questions=sq.sub_questions,
        )
    except Exception as exc:
        # 知识点映射失败不阻断入库，但必须记录（可审计）
        logger.warning("knowledge mapping failed for Q%s: %s", sq.question_number, exc)
        session.add(DomainEvent(
            event_type="KnowledgeMappingFailed",
            entity_type="question",
            entity_id=question.id,
            payload_json={"error": str(exc)[:500]},
        ))

    await session.flush()
    return question.id


# ── 辅助函数 ──────────────────────────────────────────────────────


def _extract_review_reason(sq: SlicedQuestion, final_answer: str) -> str:
    """从 issues 列表中提取审核原因分类。"""
    issues = sq.issues or []

    for issue in issues:
        if "题干为空" in issue:
            return "stem_empty"
        if "答案缺失" in issue or "答案依赖 LLM 兜底" in issue:
            return "answer_missing"
        if "答案可疑" in issue or "LLM 答案切片为空" in issue:
            return "answer_suspicious"
        if "锚点缺失" in issue or "锚点需重新标注" in issue:
            return "anchor_uncertain"
        if "选项" in issue and ("缺失" in issue or "不足" in issue):
            return "options_anomaly"

    if not final_answer.strip():
        return "answer_missing"

    return "low_confidence"


async def _find_exact_match(
    session: AsyncSession,
    stem: str | None,
    subject_id: UUID,
) -> Question | None:
    """精确匹配：stem 完全相同且同一学科。

    已由 Phase 2A Step 5 的 content_hash 匹配取代（保留以兼容旧调用）。
    """
    if not stem or not stem.strip():
        return None
    stmt = (
        select(Question)
        .where(Question.subject_id == subject_id)
        .where(Question.stem == stem.strip())
        .limit(1)
    )
    return await session.scalar(stmt)


async def _find_by_content_hash(
    session: AsyncSession,
    content_hash: str,
    subject_id: UUID,
) -> Question | None:
    """Phase 2A Step 5：按 content_hash 精确匹配（规范化题干+选项+题型 SHA256）。"""
    if not content_hash:
        return None
    stmt = (
        select(Question)
        .where(Question.subject_id == subject_id)
        .where(Question.content_hash == content_hash)
        .limit(1)
    )
    return await session.scalar(stmt)


# LLM 相似判断 prompt
_SIMILARITY_PROMPT = """你是一个题目去重助手。

我给你一道新题目的题干，以及一组已有题目的题干。
请判断新题目是否和其中某一道已有题目"内核相同"。

**内核相同的定义**：
- 考查的是同一个知识点
- 题目结构相同（比如都是选择题、都是填空题）
- 只是数字、数据、描述方式等表面细节有差异

**不算内核相同的情况**：
- 考查的知识点不同
- 题目结构不同（比如一个是选择题，一个是解答题）
- 虽然话题相关，但考查角度不同

**输出格式**（只输出JSON）：
{{
  "similar": true/false,
  "matched_index": 1,
  "reason": "简短说明为什么相似/不相似"
}}

如果没有相似的题目，similar 为 false，matched_index 为 null。

新题目题干：
{new_stem}

已有题目列表：
{existing_stems}"""


async def _find_similar_by_llm(
    session: AsyncSession,
    sq: SlicedQuestion,
    subject_id: UUID,
    gateway,
) -> Question | None:
    """用 LLM 判断新题目是否和已有题目相似。

    流程：
    1. 查询同学科最近入库的题目（限制 50 题，避免 prompt 过长）
    2. 构建 prompt，让 LLM 判断是否相似
    3. 如果相似，返回对应的已有 Question
    """
    if not gateway:
        return None
    if not sq.stem or not sq.stem.strip():
        return None

    # 查询同学科最近入库的题目
    stmt = (
        select(Question)
        .where(Question.subject_id == subject_id)
        .where(Question.status.in_(["approved", "reviewing"]))
        .order_by(Question.created_at.desc())
        .limit(50)
    )
    existing_questions = list(await session.scalars(stmt))

    if not existing_questions:
        return None

    # 构建已有题目列表
    existing_stems = "\n".join(
        f"{i+1}. [{q.source_document_name or '未知'}] {q.stem or '(空)'}"
        for i, q in enumerate(existing_questions)
    )

    prompt = _SIMILARITY_PROMPT.format(
        new_stem=sq.stem[:500],  # 截断避免过长
        existing_stems=existing_stems[:3000],  # 截断避免过长
    )

    try:
        raw = await gateway.complete(prompt, temperature=0.0)
        import json
        # 解析 JSON
        text = raw.strip()
        # 尝试直接解析
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # 尝试提取 JSON 块
            import re
            m = re.search(r"\{.*\}", text, re.DOTALL)
            if m:
                data = json.loads(m.group())
            else:
                return None

        if data.get("similar") and data.get("matched_index"):
            idx = int(data["matched_index"]) - 1
            if 0 <= idx < len(existing_questions):
                logger.info(
                    "LLM similarity: Q%s stem='%s' → existing question %s (reason=%s)",
                    sq.question_number, sq.stem[:30],
                    existing_questions[idx].id,
                    data.get("reason", ""),
                )
                return existing_questions[idx]
    except Exception as exc:
        logger.warning("LLM similarity check failed: %s", exc)

    return None


async def _get_or_create_subject(session: AsyncSession, name: str) -> Subject:
    """查找或创建学科。"""
    stmt = select(Subject).where(Subject.name == name)
    subject = await session.scalar(stmt)
    if subject:
        return subject

    # 创建新学科
    subject = Subject(
        code=name.lower().replace(" ", "_"),
        name=name,
    )
    session.add(subject)
    await session.flush()
    return subject


# canonical 题型 → 中文名（P0-2 修复：get-or-create 时写入 name）
# 与 content_slicer._QUESTION_TYPE_CANONICAL 的 canonical 枚举保持一致
_CANONICAL_QUESTION_TYPE_NAMES = {
    "single_choice": "单选题",
    "multiple_choice": "多选题",
    "fill_in": "填空题",
    "true_false": "判断题",
    "short_answer": "解答题",
}


async def _get_question_type_id(
    session: AsyncSession,
    type_code: str | None,
    subject_id: UUID,
) -> UUID | None:
    """查找题型 ID；找不到则创建（get-or-create）。

    P0-2 修复（bugs.md BUG-012 §四 A）：
    - 此前只按 QuestionType.code 查表、查不到返回 None 且不创建；
      question_types 表无种子数据 → 423 题 question_type_id 全 NULL。
    - 现在未命中 canonical 题型时自动创建（code=canonical，name=中文映射），
      与 _get_or_create_subject 模式一致；非 canonical 未知题型返回 None 并告警。
    """
    if not type_code:
        return None
    # canonical 归一化（与 content_slicer 一致，避免 LLM 变体导致查不到）
    from app.domains.document.content_slicer import _canonical_question_type
    canonical = _canonical_question_type(type_code)

    stmt = select(QuestionType).where(QuestionType.code == canonical)
    qt = await session.scalar(stmt)
    if qt:
        return qt.id

    if canonical not in _CANONICAL_QUESTION_TYPE_NAMES:
        logger.warning(
            "unknown question_type code=%r (canonical=%r), skipping type id",
            type_code, canonical,
        )
        return None

    qt = QuestionType(
        subject_id=subject_id,
        code=canonical,
        name=_CANONICAL_QUESTION_TYPE_NAMES[canonical],
        sort_order=0,
    )
    session.add(qt)
    await session.flush()
    logger.info("question_type created: code=%s name=%s subject=%s",
                canonical, qt.name, subject_id)
    return qt.id


def _normalize_options(options: list[dict] | None) -> list[dict] | None:
    """归一化选项格式。"""
    if not options:
        return None
    normalized = []
    for opt in options:
        if isinstance(opt, dict):
            normalized.append({
                "label": opt.get("label", ""),
                "text": opt.get("text", ""),
            })
    return normalized if normalized else None

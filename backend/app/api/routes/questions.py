"""Phase 2B：题库搜索与统计 API。

- GET /api/admin/questions — 条件搜索（学科/题型/知识点/年份/学校/难度/来源/状态）
- GET /api/admin/questions/{question_id} — 单题详情
- GET /api/admin/statistics — 统计聚合（题型/知识点/难度分布 + 年份趋势 + 高频知识点）
- GET /api/admin/question-candidates — 候选题目列表（review/reject）
- POST /api/admin/question-candidates/{id}/approve — 审核通过候选题
- POST /api/admin/question-candidates/{id}/reject — 拒绝候选题
- GET /api/admin/admission-metrics — 门禁通过率指标

合约见 Docs/02_Architecture/ACS.md §5.3-5.4。
"""
from uuid import UUID
import logging

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_question_application_service
from app.application.services import QuestionApplicationService
from app.core.database import get_db_session
from app.core.response import build_error, build_response
from app.models import Question, QuestionCandidate, QuestionType, Subject

router = APIRouter(prefix="/api/admin", tags=["admin questions"])

logger = logging.getLogger(__name__)

# 允许的来源类型 / 状态
SOURCE_TYPES = {"document", "generated", "student"}
QUESTION_STATUSES = {"approved", "reviewing", "rejected", "pending"}


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=build_error(code, message),
    )


async def _load_name_maps(
    session: AsyncSession,
) -> tuple[dict[str, str], dict[str, str]]:
    """加载 subject / question_type 的 id→name 映射（表很小，全量查一次）。

    供题目列表/详情序列化时附带名称，避免前端仅凭 UUID 无法展示学科/题型。
    """
    subject_names = {
        str(row.id): row.name
        for row in (await session.scalars(select(Subject))).all()
    }
    question_type_names = {
        str(row.id): row.name
        for row in (await session.scalars(select(QuestionType))).all()
    }
    return subject_names, question_type_names


async def _resolve_subject_id(session: AsyncSession, subject: str | None) -> UUID | None:
    """按 code（MATH）或 name（数学）解析学科 id。"""
    if not subject:
        return None
    stmt = select(Subject.id).where(
        (Subject.code == subject.upper()) | (Subject.name == subject)
    ).limit(1)
    return await session.scalar(stmt)


async def _resolve_question_type_id(
    session: AsyncSession, question_type: str | None
) -> UUID | None:
    """按 code（single_choice）或 name（单选题）解析题型 id。"""
    if not question_type:
        return None
    stmt = select(QuestionType.id).where(
        (QuestionType.code == question_type) | (QuestionType.name == question_type)
    ).limit(1)
    return await session.scalar(stmt)


@router.get("/catalog", response_model=None)
async def get_catalog(
    service: QuestionApplicationService = Depends(get_question_application_service),
) -> dict | JSONResponse:
    """题库目录聚合：学科 → 年级 → 题目数（管理后台题库目录树）。"""
    return build_response(await service.get_catalog())


@router.get("/questions", response_model=None)
async def search_questions(
    subject: str | None = Query(None),
    grade: str | None = Query(None),
    year: int | None = Query(None),
    school: str | None = Query(None),
    question_type: str | None = Query(None),
    knowledge_point: str | None = Query(None),
    difficulty: int | None = Query(None, ge=1, le=5),
    source_type: str | None = Query(None),
    status: str | None = Query(None),
    confidence: float | None = Query(None, ge=0, le=1),
    source_document_name: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    service: QuestionApplicationService = Depends(get_question_application_service),
) -> dict | JSONResponse:
    """条件搜索：按学科/题型/知识点/年份/学校/置信度等筛选题目。

    默认只返回 approved 状态的题目（Admission Gate v1）。
    如需查看 reviewing/rejected 题目，显式传入 status 参数。

    confidence 语义（对抗性审查 F4）：**精确匹配**（`Question.confidence == value`），
    非阈值范围。需要范围筛选（如低置信度 < 0.5）请通过 status=reviewing 组合实现，
    或后续扩展 min_confidence/max_confidence 参数。

    source_document_name：来源文档名模糊匹配（ilike %..%），供管理后台
    「从文档列表查看入库题目」入口使用。
    """
    # Admission Gate v1：默认只查 approved
    if status is None:
        status = "approved"
    if source_type is not None and source_type not in SOURCE_TYPES:
        return _error_response(400, "VALIDATION_ERROR", f"Unsupported source_type: {source_type}")
    if status is not None and status not in QUESTION_STATUSES:
        return _error_response(400, "VALIDATION_ERROR", f"Unsupported status: {status}")

    subject_id = await _resolve_subject_id(session, subject)
    question_type_id = await _resolve_question_type_id(session, question_type)

    items, total = await service.search_questions(
        subject_id=subject_id,
        grade=grade,
        year=year,
        school=school,
        question_type_id=question_type_id,
        knowledge_point=knowledge_point,
        difficulty=difficulty,
        source_type=source_type,
        status=status,
        confidence=confidence,
        source_document_name=source_document_name,
        page=page,
        page_size=page_size,
    )
    subject_names, question_type_names = await _load_name_maps(session)
    return build_response(
        {
            "items": [
                _serialize_question(q, subject_names, question_type_names)
                for q in items
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.get("/questions/{question_id}", response_model=None)
async def get_question(
    question_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    service: QuestionApplicationService = Depends(get_question_application_service),
) -> dict | JSONResponse:
    """单题详情：内容、答案、详解、配图、元数据和出现次数（ACS §5.3 合约）。

    Phase 2B 修复（对抗性审查 F1）：配图查询和 occurrence_count 派生下沉到
    Repository/Service 层（不再在 API 层直连表），SQL 可被真实 DB 集成测试覆盖。
    """
    question, images, occurrence_count = await service.get_question_detail(question_id)
    if question is None:
        return _error_response(404, "NOT_FOUND", "Question not found")

    subject_names, question_type_names = await _load_name_maps(session)
    data = _serialize_question(question, subject_names, question_type_names)
    data["occurrence_count"] = occurrence_count
    data["images"] = [
        {
            "image_key": img.image_key,
            "image_type": img.image_type,
            "description": img.description,
            "image_order": img.image_order,
            "page_no": img.page_no,
            "bbox": img.bbox,
            "placement": img.placement,
            "sub_question_qno": getattr(img, "sub_question_qno", None),
            "source": img.source,
            "figure_id": img.figure_id,
            "url": img.url,  # 2026-08-27：OCR 图片 URL（新数据有值，历史数据为空）
        }
        for img in images
    ]
    return build_response(data)


@router.get("/statistics", response_model=None)
async def get_statistics(
    start_year: int | None = Query(None),
    end_year: int | None = Query(None),
    subject: str | None = Query(None),
    grade: str | None = Query(None),
    knowledge_point: str | None = Query(None),
    question_type: str | None = Query(None),
    session: AsyncSession = Depends(get_db_session),
    service: QuestionApplicationService = Depends(get_question_application_service),
) -> dict | JSONResponse:
    """统计聚合：total / question_type_distribution / knowledge_point_distribution /
    difficulty_distribution / year_trend / kp_year_trend（ACS §5.4 合约）。

    start_year/end_year 全局过滤（对抗性审查 F3）：在 repository _base() 统一处理，
    影响 total 和所有 distribution，不只是 trend。
    """
    subject_id = await _resolve_subject_id(session, subject)
    question_type_id = await _resolve_question_type_id(session, question_type)

    stats = await service.get_statistics(
        subject_id=subject_id,
        grade=grade,
        year=None,  # 单年筛选由 start_year/end_year 范围替代
        school=None,
        question_type_id=question_type_id,
        knowledge_point=knowledge_point,
        start_year=start_year,
        end_year=end_year,
    )
    return build_response(stats)


def _serialize_question(
    q: Question,
    subject_names: dict[str, str] | None = None,
    question_type_names: dict[str, str] | None = None,
) -> dict:
    return {
        "id": str(q.id),
        "subject_id": str(q.subject_id),
        "subject_name": (subject_names or {}).get(str(q.subject_id)),
        "grade": q.grade,
        "question_type_id": str(q.question_type_id) if q.question_type_id else None,
        "question_type_name": (question_type_names or {}).get(str(q.question_type_id))
        if q.question_type_id else None,
        "original_question_type": q.original_question_type,
        "section_id": q.section_id,
        "stem": q.stem,
        "options": q.options,
        "answer": q.answer,
        "answer_structure": getattr(q, "answer_structure", None),
        "word_bank": getattr(q, "word_bank", None),
        "explanation": q.explanation,
        "difficulty": q.difficulty,
        "score": float(q.score) if q.score is not None else None,
        "source_type": q.source_type,
        "source_document_name": q.source_document_name,
        "status": q.status,
        "confidence": float(q.confidence) if q.confidence is not None else None,
        "occurrence_count": q.occurrence_count,
        "is_composite": q.is_composite,
        # P4E.1（2026-08-27）：返回子题完整内容（此前 API 不返回
        # sub_questions，前端无法显示子题题干/选项，LOG v6.43 链路断裂 #5）。
        "sub_questions": getattr(q, "sub_questions", None),
        # 展示契约 v0.4 字段（2026-08-30）
        "stem_line_ids": getattr(q, "stem_line_ids", None),
        "answer_line_ids": getattr(q, "answer_line_ids", None),
        "explanation_line_ids": getattr(q, "explanation_line_ids", None),
        "shared_material_line_ids": getattr(q, "shared_material_line_ids", None),
        "shared_material_notes_line_ids": getattr(q, "shared_material_notes_line_ids", None),
        "stem_region": getattr(q, "stem_region", None),
        "answer_region": getattr(q, "answer_region", None),
        "explanation_region": getattr(q, "explanation_region", None),
        "scoring_standard": getattr(q, "scoring_standard", None),
        "shared_material": getattr(q, "shared_material", None),
        "shared_material_notes": getattr(q, "shared_material_notes", None),
        "answer_images": getattr(q, "answer_images", None),
        "created_at": q.created_at.isoformat() if q.created_at else None,
    }


# ═══════════════════════════════════════════════════════════════════
# Phase 4：Admission Gate 候选闭环 API
# ═══════════════════════════════════════════════════════════════════


@router.get("/question-candidates", response_model=None)
async def list_question_candidates(
    gate_decision: str | None = Query(None, description="review / reject"),
    subject: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
) -> dict | JSONResponse:
    """候选题目列表：查看 review/reject 的题目，支持审核操作。"""
    stmt = select(QuestionCandidate)
    count_stmt = select(func.count()).select_from(QuestionCandidate)

    if gate_decision:
        stmt = stmt.where(QuestionCandidate.gate_decision == gate_decision)
        count_stmt = count_stmt.where(QuestionCandidate.gate_decision == gate_decision)

    if subject:
        subject_id = await _resolve_subject_id(session, subject)
        if subject_id:
            stmt = stmt.where(QuestionCandidate.subject_id == subject_id)
            count_stmt = count_stmt.where(QuestionCandidate.subject_id == subject_id)

    total = await session.scalar(count_stmt)
    stmt = stmt.order_by(QuestionCandidate.created_at.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    candidates = (await session.scalars(stmt)).all()

    return build_response({
        "items": [
            {
                "id": str(c.id),
                "stem": c.stem[:200],
                "question_type": c.question_type_id,
                "gate_decision": c.gate_decision,
                "gate_reason": c.gate_reason,
                "confidence": float(c.confidence) if c.confidence else None,
                "source_document_name": c.source_document_name,
                "document_id": str(c.document_id),
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in candidates
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.post("/question-candidates/{candidate_id}/approve", response_model=None)
async def approve_candidate(
    candidate_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict | JSONResponse:
    """审核通过候选题：将候选题迁移到 questions 表（status=approved）。"""
    candidate = await session.get(QuestionCandidate, candidate_id)
    if candidate is None:
        return _error_response(404, "NOT_FOUND", "Candidate not found")

    # content_hash 去重：同一 content_hash 已在 questions 表中 → 拒绝
    if candidate.content_hash:
        existing_q = await session.scalar(
            select(Question).where(
                Question.content_hash == candidate.content_hash
            ).limit(1)
        )
        if existing_q is not None:
            return _error_response(
                409, "CONFLICT",
                f"Question with same content_hash already exists: {existing_q.id}",
            )

    # 创建 Question 记录
    question = Question(
        subject_id=candidate.subject_id,
        grade=candidate.grade,
        question_type_id=candidate.question_type_id,
        score=candidate.score,
        difficulty=candidate.difficulty,
        stem=candidate.stem,
        options=candidate.options,
        answer=candidate.answer,
        answer_structure=candidate.answer_structure,
        word_bank=candidate.word_bank,
        explanation=candidate.explanation,
        source_type=candidate.source_type,
        source_document_name=candidate.source_document_name,
        status="approved",
        confidence=candidate.confidence,
        content_hash=candidate.content_hash,
        is_composite=candidate.is_composite,
        original_question_type=candidate.original_question_type,
        section_id=candidate.section_id,
        sub_questions=candidate.sub_questions,
        stem_line_ids=candidate.stem_line_ids,
        answer_line_ids=candidate.answer_line_ids,
        explanation_line_ids=candidate.explanation_line_ids,
        shared_material_line_ids=candidate.shared_material_line_ids,
        shared_material_notes_line_ids=candidate.shared_material_notes_line_ids,
        stem_region=candidate.stem_region,
        answer_region=candidate.answer_region,
        explanation_region=candidate.explanation_region,
        scoring_standard=candidate.scoring_standard,
        shared_material=candidate.shared_material,
        shared_material_notes=candidate.shared_material_notes,
        answer_images=candidate.answer_images,
        occurrence_count=1,
    )
    session.add(question)
    await session.flush()

    # 删除候选记录
    await session.delete(candidate)
    await session.flush()

    logger.info("candidate approved: %s → question %s", candidate_id, question.id)
    return build_response({"question_id": str(question.id), "status": "approved"})


@router.post("/question-candidates/{candidate_id}/reject", response_model=None)
async def reject_candidate(
    candidate_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict | JSONResponse:
    """拒绝候选题：删除候选记录。"""
    candidate = await session.get(QuestionCandidate, candidate_id)
    if candidate is None:
        return _error_response(404, "NOT_FOUND", "Candidate not found")

    await session.delete(candidate)
    await session.flush()

    logger.info("candidate rejected: %s", candidate_id)
    return build_response({"status": "rejected"})


@router.get("/admission-metrics", response_model=None)
async def get_admission_metrics(
    session: AsyncSession = Depends(get_db_session),
) -> dict | JSONResponse:
    """门禁通过率指标：approved/review/reject 数量和比例。"""
    total_q = await session.scalar(select(func.count()).select_from(Question))
    approved_q = await session.scalar(
        select(func.count()).select_from(Question).where(Question.status == "approved")
    )
    reviewing_q = await session.scalar(
        select(func.count()).select_from(Question).where(Question.status == "reviewing")
    )
    total_c = await session.scalar(select(func.count()).select_from(QuestionCandidate))
    review_c = await session.scalar(
        select(func.count()).select_from(QuestionCandidate).where(
            QuestionCandidate.gate_decision == "review"
        )
    )
    reject_c = await session.scalar(
        select(func.count()).select_from(QuestionCandidate).where(
            QuestionCandidate.gate_decision == "reject"
        )
    )

    return build_response({
        "questions": {
            "total": total_q or 0,
            "approved": approved_q or 0,
            "reviewing": reviewing_q or 0,
        },
        "candidates": {
            "total": total_c or 0,
            "review": review_c or 0,
            "reject": reject_c or 0,
        },
    })

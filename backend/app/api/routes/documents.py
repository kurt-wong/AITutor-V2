from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Body, Depends, File, Form, Query, UploadFile
from fastapi.responses import JSONResponse

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_document_application_service
from app.application.services import DocumentApplicationService
from app.core.database import get_db_session
from app.core.response import build_error, build_response
from app.infrastructure.storage import StorageError
from app.models import Document, DocumentProcessingLog, BackgroundTask

router = APIRouter(prefix="/api/admin/documents", tags=["admin documents"])

ALLOWED_EXTENSIONS = {".pdf", ".docx"}
ALLOWED_STATUSES = {"queued", "pending", "processing", "completed", "failed"}
REVIEW_STATUSES = {"pending", "approved", "rejected"}


@router.post("/upload", response_model=None)
async def upload_documents(
    files: list[UploadFile] = File(...),
    subject: str | None = Form(None),
    grade: str | None = Form(None),
    year: int | None = Form(None),
    service: DocumentApplicationService = Depends(get_document_application_service),
) -> dict | JSONResponse:
    document_ids: list[str] = []
    task_ids: list[str] = []
    for upload in files:
        filename = Path(upload.filename or "").name
        extension = Path(filename).suffix.lower()
        if not filename or extension not in ALLOWED_EXTENSIONS:
            return _error_response(
                400,
                "VALIDATION_ERROR",
                f"Unsupported file type: {filename}",
            )
        try:
            document, task = await service.upload_document(
                filename=filename,
                file_type=extension.lstrip("."),
                file_obj=upload.file,
                size=upload.size or 0,
                content_type=upload.content_type or "application/octet-stream",
                subject=subject,
                grade=grade,
                year=year,
            )
        except StorageError as exc:
            return _error_response(500, "UPLOAD_FAILED", str(exc))
        document_ids.append(str(document.id))
        task_ids.append(str(task.id))
    return build_response(
        {
            "task_ids": task_ids,
            "document_ids": document_ids,
            "status": "queued",
        }
    )


@router.get("", response_model=None)
async def list_documents(
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: DocumentApplicationService = Depends(get_document_application_service),
) -> dict | JSONResponse:
    if status is not None and status not in ALLOWED_STATUSES:
        return _error_response(400, "VALIDATION_ERROR", f"Unsupported status: {status}")
    items, total = await service.list_documents(
        status=status,
        page=page,
        page_size=page_size,
    )
    return build_response(
        {
            "items": [_serialize_document(item) for item in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.get("/{document_id}", response_model=None)
async def get_document(
    document_id: UUID,
    service: DocumentApplicationService = Depends(get_document_application_service),
) -> dict | JSONResponse:
    document = await service.get_document(document_id)
    if document is None:
        return _error_response(404, "NOT_FOUND", "Document not found")
    return build_response(_serialize_document(document))


@router.get("/{document_id}/status", response_model=None)
async def get_document_status(
    document_id: UUID,
    service: DocumentApplicationService = Depends(get_document_application_service),
) -> dict | JSONResponse:
    result = await service.get_document_status(document_id)
    if result is None:
        return _error_response(404, "NOT_FOUND", "Document not found")
    document, task = result
    status, progress, stage, error_message = _document_status(document, task)
    return build_response(
        {
            "status": status,
            "progress": progress,
            "current_stage": stage,
            "error_message": error_message,
        }
    )


@router.get("/{document_id}/parse-result", response_model=None)
async def get_document_parse_result(
    document_id: UUID,
    service: DocumentApplicationService = Depends(get_document_application_service),
) -> dict | JSONResponse:
    result = await service.get_document_status(document_id)
    if result is None:
        return _error_response(404, "NOT_FOUND", "Document not found")
    document, task = result
    return build_response(_serialize_parse_result(document, task))


@router.post("/{document_id}/retry", response_model=None)
async def retry_document(
    document_id: UUID,
    service: DocumentApplicationService = Depends(get_document_application_service),
) -> dict | JSONResponse:
    task = await service.retry_document(document_id)
    if task is None:
        return _error_response(404, "NOT_FOUND", "Document not found")
    return build_response(
        {
            "task_id": str(task.id),
            "document_id": str(document_id),
            "status": task.status,
        }
    )


@router.get("/{document_id}/logs", response_model=None)
async def get_document_logs(
    document_id: UUID,
    service: DocumentApplicationService = Depends(get_document_application_service),
) -> dict | JSONResponse:
    logs = await service.get_document_logs(document_id)
    if logs is None:
        return _error_response(404, "NOT_FOUND", "Document not found")
    return build_response({"items": [_serialize_log(log) for log in logs]})


@router.put("/{document_id}/review", response_model=None)
async def update_document_review(
    document_id: UUID,
    body: dict = Body(...),
    service: DocumentApplicationService = Depends(get_document_application_service),
) -> dict | JSONResponse:
    question_number = str(body.get("question_number") or "").strip()
    status = str(body.get("status") or "").strip()
    if not question_number:
        return _error_response(400, "VALIDATION_ERROR", "question_number is required")
    if status not in REVIEW_STATUSES:
        return _error_response(
            400,
            "VALIDATION_ERROR",
            f"Unsupported review status: {status}",
        )
    comment = body.get("comment")
    if comment is not None and not isinstance(comment, str):
        return _error_response(400, "VALIDATION_ERROR", "comment must be a string")
    overrides = body.get("overrides")
    if overrides is not None and not isinstance(overrides, dict):
        return _error_response(400, "VALIDATION_ERROR", "overrides must be an object")
    question_id_raw = body.get("question_id")
    question_id: UUID | None = None
    if question_id_raw is not None:
        try:
            question_id = UUID(str(question_id_raw))
        except ValueError:
            return _error_response(400, "VALIDATION_ERROR", "question_id must be a UUID")

    task, error_code = await service.update_document_review(
        document_id,
        question_number=question_number,
        status=status,
        comment=comment,
        overrides=overrides,
        question_id=question_id,
    )
    if task is None:
        if error_code == "REVIEW_NOT_READY":
            return _error_response(409, "REVIEW_NOT_READY", "Parse result is not ready")
        if error_code == "QUESTION_NOT_FOUND":
            return _error_response(
                404,
                "QUESTION_NOT_FOUND",
                f"Question {question_number} not found in document {document_id}",
            )
        return _error_response(404, "NOT_FOUND", "Document not found")

    decisions = (task.result_json or {}).get("review_decisions", {})
    decision = decisions.get(question_number, {})
    overrides_by_question = (task.result_json or {}).get("review_overrides", {})
    override = overrides_by_question.get(question_number, {})
    return build_response(
        {
            "document_id": str(document_id),
            "question_number": question_number,
            "status": decision.get("status", status),
            "comment": decision.get("comment", ""),
            "updated_at": decision.get("updated_at"),
            "overrides": override,
        }
    )


def _serialize_document(document: Document) -> dict:
    return {
        "id": str(document.id),
        "filename": document.filename,
        "file_type": document.file_type,
        "object_key": document.object_key,
        "subject": document.subject,
        "grade": document.grade,
        "year": document.year,
        "school": document.school,
        "upload_status": document.upload_status,
        "processing_status": document.processing_status,
        "error_message": document.error_message,
        "created_at": document.created_at.isoformat(),
        "updated_at": document.updated_at.isoformat(),
    }


def _serialize_log(log: DocumentProcessingLog) -> dict:
    return {
        "id": str(log.id),
        "document_id": str(log.document_id),
        "stage": log.stage,
        "message": log.message,
        "created_at": log.created_at.isoformat(),
    }


def _document_status(
    document: Document,
    task: BackgroundTask | None,
) -> tuple[str, float | None, str | None, str | None]:
    if task is not None:
        progress = float(task.progress) if task.progress is not None else None
        return (
            task.status,
            progress,
            task.current_stage,
            task.error_detail or document.error_message,
        )
    return (
        document.processing_status,
        None,
        None,
        document.error_message,
    )


def _serialize_parse_result(
    document: Document,
    task: BackgroundTask | None,
) -> dict:
    status, progress, stage, error_message = _document_status(document, task)
    return {
        "task_id": str(task.id) if task is not None else None,
        "document_id": str(document.id),
        "status": status,
        "progress": progress,
        "current_stage": stage,
        "error_message": error_message,
        "result": task.result_json if task is not None else None,
    }


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=build_error(code, message),
    )


# ── 答案提取重试 API ──────────────────────────────────────────────────


@router.get("/answer-retries")
async def list_answer_retries(
    status: str | None = Query(None, description="pending / retrying / succeeded / failed"),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """查看答案提取重试队列。"""
    from app.domains.document.retry_repository import AnswerExtractionRetryRepository
    repo = AnswerExtractionRetryRepository(session)
    from sqlalchemy import select
    from app.models import AnswerExtractionRetry
    stmt = select(AnswerExtractionRetry).order_by(AnswerExtractionRetry.created_at.desc())
    if status:
        stmt = stmt.where(AnswerExtractionRetry.status == status)
    stmt = stmt.limit(50)
    items = list(await session.scalars(stmt))
    return build_response({
        "items": [
            {
                "id": str(item.id),
                "document_id": str(item.document_id),
                "status": item.status,
                "retry_count": item.retry_count,
                "max_retries": item.max_retries,
                "error_detail": item.error_detail,
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "last_retry_at": item.last_retry_at.isoformat() if item.last_retry_at else None,
            }
            for item in items
        ],
        "total": len(items),
    })


@router.post("/answer-retries/{retry_id}/retry", response_model=None)
async def trigger_answer_retry(
    retry_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict | JSONResponse:
    """人工触发重试：重置重试记录为 pending 状态。"""
    from app.domains.document.retry_repository import AnswerExtractionRetryRepository
    repo = AnswerExtractionRetryRepository(session)
    item = await repo.reset_to_pending(retry_id)
    if item is None:
        return _error_response(404, "NOT_FOUND", "Retry record not found")
    await session.commit()
    return build_response({
        "id": str(item.id),
        "status": item.status,
        "message": "已重置为 pending，等待下次轮询自动重试",
    })

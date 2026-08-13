from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import JSONResponse

from app.api.dependencies import get_document_application_service
from app.application.services import DocumentApplicationService
from app.core.response import build_error, build_response
from app.infrastructure.storage import StorageError
from app.models import Document, DocumentProcessingLog, BackgroundTask

router = APIRouter(prefix="/api/admin/documents", tags=["admin documents"])

ALLOWED_EXTENSIONS = {".pdf", ".docx"}
ALLOWED_STATUSES = {"queued", "pending", "processing", "completed", "failed"}


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


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=build_error(code, message),
    )

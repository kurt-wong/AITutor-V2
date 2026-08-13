from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.api.dependencies import get_task_application_service
from app.application.services import TaskApplicationService
from app.core.response import build_error, build_response
from app.models import BackgroundTask

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("", response_model=None)
async def list_tasks(
    task_type: str | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: TaskApplicationService = Depends(get_task_application_service),
) -> dict:
    items, total = await service.list_tasks(
        task_type=task_type,
        status=status,
        page=page,
        page_size=page_size,
    )
    return build_response(
        {
            "items": [_serialize_task(item) for item in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.get("/{task_id}", response_model=None)
async def get_task(
    task_id: UUID,
    service: TaskApplicationService = Depends(get_task_application_service),
) -> dict | JSONResponse:
    task = await service.get_task(task_id)
    if task is None:
        return _error_response(404, "TASK_NOT_FOUND", "Task not found")
    return build_response(_serialize_task(task))


@router.post("/{task_id}/retry", response_model=None)
async def retry_task(
    task_id: UUID,
    service: TaskApplicationService = Depends(get_task_application_service),
) -> dict | JSONResponse:
    task = await service.get_task(task_id)
    if task is None:
        return _error_response(404, "TASK_NOT_FOUND", "Task not found")
    if task.status != "failed":
        return _error_response(409, "TASK_RETRY_INVALID", "Only failed tasks can be retried")
    task = await service.retry_task(task_id)
    return build_response(_serialize_task(task))


def _serialize_task(task: BackgroundTask) -> dict:
    return {
        "id": str(task.id),
        "task_type": task.task_type,
        "status": task.status,
        "progress": float(task.progress) if task.progress is not None else None,
        "current_stage": task.current_stage,
        "error_detail": task.error_detail,
        "payload": task.payload_json,
        "result": task.result_json,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
    }


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=build_error(code, message),
    )

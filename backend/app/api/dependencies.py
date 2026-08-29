from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services import (
    DocumentApplicationService,
    QuestionApplicationService,
    TaskApplicationService,
)
from app.core.config import settings
from app.core.database import get_db_session
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


async def verify_admin_key(
    x_api_key: str | None = Header(None, alias="X-API-Key"),
) -> None:
    """Admin API key verification. Reads ADMIN_API_KEY from config.

    Skipped in development when key is the default 'change-me'.
    """
    expected = settings.admin_api_key
    if expected == "change-me":
        return  # dev mode, skip auth
    if x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def get_minio_storage() -> MinIOStorage:
    return MinIOStorage()


def get_document_application_service(
    session: AsyncSession = Depends(get_db_session),
    storage: MinIOStorage = Depends(get_minio_storage),
) -> DocumentApplicationService:
    document_repository = DocumentRepository(session)
    log_repository = DocumentProcessingLogRepository(session)
    task_repository = BackgroundTaskRepository(session)
    event_repository = DomainEventRepository(session)
    question_repository = QuestionRepository(session)
    return DocumentApplicationService(
        document_service=DocumentService(
            document_repository=document_repository,
            log_repository=log_repository,
        ),
        task_service=TaskService(repository=task_repository),
        event_service=EventService(repository=event_repository),
        storage=storage,
        question_service=QuestionService(repository=question_repository),
    )


def get_task_application_service(
    session: AsyncSession = Depends(get_db_session),
) -> TaskApplicationService:
    task_repository = BackgroundTaskRepository(session)
    event_repository = DomainEventRepository(session)
    return TaskApplicationService(
        task_service=TaskService(repository=task_repository),
        event_service=EventService(repository=event_repository),
    )


def get_question_application_service(
    session: AsyncSession = Depends(get_db_session),
) -> QuestionApplicationService:
    """Phase 2B：题库搜索/统计 Application Service。"""
    question_repository = QuestionRepository(session)
    event_repository = DomainEventRepository(session)
    return QuestionApplicationService(
        question_service=QuestionService(repository=question_repository),
        event_service=EventService(repository=event_repository),
    )

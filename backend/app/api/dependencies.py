from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services import (
    DocumentApplicationService,
    TaskApplicationService,
)
from app.core.database import get_db_session
from app.domains.document.repository import (
    DocumentProcessingLogRepository,
    DocumentRepository,
)
from app.domains.document.service import DocumentService
from app.domains.event.repository import DomainEventRepository
from app.domains.event.service import EventService
from app.domains.task.repository import BackgroundTaskRepository
from app.domains.task.service import TaskService
from app.infrastructure.storage import MinIOStorage


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
    return DocumentApplicationService(
        document_service=DocumentService(
            document_repository=document_repository,
            log_repository=log_repository,
        ),
        task_service=TaskService(repository=task_repository),
        event_service=EventService(repository=event_repository),
        storage=storage,
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

from decimal import Decimal
from pathlib import Path
from typing import Any
from typing import BinaryIO
from uuid import UUID
from uuid import uuid4

from app.domains.document.service import DocumentService
from app.domains.event.service import EventService
from app.domains.question.service import QuestionService
from app.domains.task.service import TaskService
from app.infrastructure.storage import MinIOStorage
from app.models import BackgroundTask, Document, Question


class TaskApplicationService:
    def __init__(
        self,
        task_service: TaskService,
        event_service: EventService,
    ) -> None:
        self.task_service = task_service
        self.event_service = event_service

    async def create_and_queue(
        self,
        *,
        task_type: str,
        payload: dict[str, Any] | None = None,
    ) -> BackgroundTask:
        task = await self.task_service.create_task(task_type=task_type, payload=payload)
        await self.event_service.publish(
            event_type="TaskQueued",
            entity_type="background_task",
            entity_id=task.id,
            payload={"task_type": task.task_type},
        )
        await self.task_service.commit()
        await self.event_service.commit()
        return task

    async def list_tasks(
        self,
        *,
        task_type: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[BackgroundTask], int]:
        skip = (page - 1) * page_size
        items = await self.task_service.list_tasks(
            task_type=task_type,
            status=status,
            skip=skip,
            limit=page_size,
        )
        total = await self.task_service.count_tasks(
            task_type=task_type,
            status=status,
        )
        return items, total

    async def get_task(self, task_id: UUID) -> BackgroundTask | None:
        return await self.task_service.get_task(task_id)

    async def retry_task(self, task_id: UUID) -> BackgroundTask | None:
        task = await self.task_service.get_task(task_id)
        if task is None:
            return None
        if task.status != "failed":
            return task
        task = await self.task_service.retry_task(task_id)
        await self.event_service.publish(
            event_type="TaskQueued",
            entity_type="background_task",
            entity_id=task.id,
            payload={"task_type": task.task_type},
        )
        await self.task_service.commit()
        await self.event_service.commit()
        return task


class DocumentApplicationService:
    def __init__(
        self,
        document_service: DocumentService,
        task_service: TaskService,
        event_service: EventService,
        storage: MinIOStorage,
    ) -> None:
        self.document_service = document_service
        self.task_service = task_service
        self.event_service = event_service
        self.storage = storage

    async def upload_document(
        self,
        *,
        filename: str,
        file_type: str,
        file_obj: BinaryIO,
        size: int,
        content_type: str,
        subject: str | None = None,
        grade: str | None = None,
        year: int | None = None,
        school: str | None = None,
    ) -> tuple[Document, BackgroundTask]:
        object_key = f"documents/{uuid4().hex}/{Path(filename).name}"
        self.storage.put_object(
            object_key=object_key,
            file_obj=file_obj,
            size=size,
            content_type=content_type,
        )
        document = await self.document_service.register_document(
            filename=filename,
            file_type=file_type,
            object_key=object_key,
            subject=subject,
            grade=grade,
            year=year,
            school=school,
        )
        task = await self.task_service.create_task(
            task_type="document_parse",
            payload={"document_id": str(document.id)},
        )
        await self.event_service.publish(
            event_type="DocumentUploaded",
            entity_type="document",
            entity_id=document.id,
            payload={"document_id": str(document.id), "task_id": str(task.id)},
        )
        await self.document_service.commit()
        await self.task_service.commit()
        await self.event_service.commit()
        return document, task

    async def list_documents(
        self,
        *,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Document], int]:
        skip = (page - 1) * page_size
        items = await self.document_service.list_documents(
            status=status,
            skip=skip,
            limit=page_size,
        )
        total = await self.document_service.count_documents(status=status)
        return items, total

    async def get_document(self, document_id: UUID) -> Document | None:
        return await self.document_service.get_document(document_id)

    async def get_document_status(
        self,
        document_id: UUID,
    ) -> tuple[Document, BackgroundTask | None] | None:
        document = await self.document_service.get_document(document_id)
        if document is None:
            return None
        task = await self.task_service.latest_for_document(document_id)
        return document, task

    async def retry_document(self, document_id: UUID) -> BackgroundTask | None:
        document = await self.document_service.get_document(document_id)
        if document is None:
            return None
        self.document_service.reset_for_retry(document)
        task = await self.task_service.create_task(
            task_type="document_parse",
            payload={"document_id": str(document.id)},
        )
        await self.event_service.publish(
            event_type="DocumentRetryQueued",
            entity_type="document",
            entity_id=document.id,
            payload={"document_id": str(document.id), "task_id": str(task.id)},
        )
        await self.document_service.add_log(
            document.id,
            stage="retry",
            message="Document parse retry queued",
        )
        await self.document_service.commit()
        await self.task_service.commit()
        await self.event_service.commit()
        return task

    async def get_document_logs(
        self,
        document_id: UUID,
    ) -> list[Any] | None:
        document = await self.document_service.get_document(document_id)
        if document is None:
            return None
        return await self.document_service.get_logs(document_id)


class QuestionApplicationService:
    def __init__(
        self,
        question_service: QuestionService,
        event_service: EventService,
    ) -> None:
        self.question_service = question_service
        self.event_service = event_service

    async def create_question(
        self,
        *,
        subject_id: UUID,
        stem: str,
        options: list[dict[str, Any]] | None = None,
        answer: str | None = None,
        explanation: str | None = None,
        grade: str | None = None,
        year: int | None = None,
        school: str | None = None,
        question_type_id: UUID | None = None,
        score: Decimal | None = None,
        difficulty: int | None = None,
        source_type: str = "document",
        source_document_name: str | None = None,
        confidence: Decimal | None = None,
    ) -> Question:
        question = await self.question_service.create_question(
            subject_id=subject_id,
            stem=stem,
            options=options,
            answer=answer,
            explanation=explanation,
            grade=grade,
            year=year,
            school=school,
            question_type_id=question_type_id,
            score=score,
            difficulty=difficulty,
            source_type=source_type,
            source_document_name=source_document_name,
            confidence=confidence,
        )
        await self.event_service.publish(
            event_type="QuestionCreated",
            entity_type="question",
            entity_id=question.id,
            payload={"question_id": str(question.id)},
        )
        await self.question_service.commit()
        await self.event_service.commit()
        return question

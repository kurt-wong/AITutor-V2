from uuid import UUID

from app.domains.document.repository import (
    DocumentProcessingLogRepository,
    DocumentRepository,
)
from app.models import Document, DocumentProcessingLog


class DocumentService:
    def __init__(
        self,
        document_repository: DocumentRepository,
        log_repository: DocumentProcessingLogRepository,
    ) -> None:
        self.document_repository = document_repository
        self.log_repository = log_repository

    async def register_document(
        self,
        *,
        filename: str,
        file_type: str,
        object_key: str,
        subject: str | None = None,
        grade: str | None = None,
        year: int | None = None,
        school: str | None = None,
    ) -> Document:
        document = Document(
            filename=filename,
            file_type=file_type,
            object_key=object_key,
            subject=subject,
            grade=grade,
            year=year,
            school=school,
            upload_status="queued",
            processing_status="pending",
        )
        await self.document_repository.add(document)
        await self.log_repository.add(
            DocumentProcessingLog(
                document_id=document.id,
                stage="upload",
                message="Document uploaded",
            )
        )
        return document

    async def commit(self) -> None:
        await self.document_repository.commit()

    async def get_document(self, document_id: UUID) -> Document | None:
        return await self.document_repository.get(document_id)

    async def list_documents(
        self,
        *,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Document]:
        return await self.document_repository.list_by_status(
            status=status,
            skip=skip,
            limit=limit,
        )

    async def count_documents(self, *, status: str | None = None) -> int:
        return await self.document_repository.count_by_status(status=status)

    async def get_logs(self, document_id: UUID) -> list[DocumentProcessingLog]:
        return await self.log_repository.list_by_document(document_id)

    async def add_log(
        self,
        document_id: UUID,
        *,
        stage: str,
        message: str,
    ) -> None:
        await self.log_repository.add(
            DocumentProcessingLog(
                document_id=document_id,
                stage=stage,
                message=message,
            )
        )

    def reset_for_retry(self, document: Document) -> None:
        document.processing_status = "pending"
        document.error_message = None

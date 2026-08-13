from uuid import UUID

from sqlalchemy import or_, select

from app.models import Document, DocumentProcessingLog
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    model = Document

    async def list_by_status(
        self,
        *,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Document]:
        stmt = select(Document).order_by(Document.created_at.desc())
        if status:
            stmt = stmt.where(_status_clause(status))
        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.scalars(stmt)
        return list(result)

    async def count_by_status(self, *, status: str | None = None) -> int:
        stmt = select(Document.id)
        if status:
            stmt = stmt.where(_status_clause(status))
        result = await self.session.scalars(stmt)
        return len(list(result))


class DocumentProcessingLogRepository(BaseRepository[DocumentProcessingLog]):
    model = DocumentProcessingLog

    async def list_by_document(self, document_id: UUID) -> list[DocumentProcessingLog]:
        stmt = (
            select(DocumentProcessingLog)
            .where(DocumentProcessingLog.document_id == document_id)
            .order_by(DocumentProcessingLog.created_at)
        )
        result = await self.session.scalars(stmt)
        return list(result)


def _status_clause(status: str):
    if status == "queued":
        return Document.upload_status == "queued"
    if status == "pending":
        return Document.processing_status == "pending"
    if status == "processing":
        return or_(
            Document.upload_status == "processing",
            Document.processing_status.in_(("parsing", "annotating", "reviewing")),
        )
    if status == "completed":
        return or_(
            Document.upload_status == "completed",
            Document.processing_status == "completed",
        )
    if status == "failed":
        return or_(
            Document.upload_status == "failed",
            Document.processing_status == "failed",
        )
    return Document.upload_status == status

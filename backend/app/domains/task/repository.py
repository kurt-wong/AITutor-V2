from uuid import UUID

from sqlalchemy import select

from app.models import BackgroundTask
from app.repositories.base import BaseRepository


class BackgroundTaskRepository(BaseRepository[BackgroundTask]):
    model = BackgroundTask

    async def list_by_filters(
        self,
        *,
        task_type: str | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[BackgroundTask]:
        stmt = select(BackgroundTask).order_by(BackgroundTask.created_at.desc())
        if task_type:
            stmt = stmt.where(BackgroundTask.task_type == task_type)
        if status:
            stmt = stmt.where(BackgroundTask.status == status)
        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.scalars(stmt)
        return list(result)

    async def count_by_filters(
        self,
        *,
        task_type: str | None = None,
        status: str | None = None,
    ) -> int:
        stmt = select(BackgroundTask.id)
        if task_type:
            stmt = stmt.where(BackgroundTask.task_type == task_type)
        if status:
            stmt = stmt.where(BackgroundTask.status == status)
        result = await self.session.scalars(stmt)
        return len(list(result))

    async def latest_for_document(self, document_id: UUID) -> BackgroundTask | None:
        stmt = (
            select(BackgroundTask)
            .where(BackgroundTask.payload_json["document_id"].astext == str(document_id))
            .order_by(BackgroundTask.created_at.desc())
            .limit(1)
        )
        return await self.session.scalar(stmt)

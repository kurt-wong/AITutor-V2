from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

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

    async def list_stale_running(
        self,
        *,
        task_type: str,
        active_task_id: UUID | None,
        stale_after_seconds: int = 900,
    ) -> list[BackgroundTask]:
        """列出超时未更新的 running 任务（worker 重启/崩溃遗留的僵尸任务）。

        - 排除当前 worker 正在处理的任务（active_task_id 豁免）；
        - 只挑 updated_at 距今超过 stale_after_seconds 的（防误伤刚启动任务）。
        """
        from datetime import datetime, timedelta, timezone

        stmt = select(BackgroundTask).where(
            BackgroundTask.task_type == task_type,
            BackgroundTask.status == "running",
        )
        if active_task_id is not None:
            stmt = stmt.where(BackgroundTask.id != active_task_id)
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=stale_after_seconds)
        stmt = stmt.where(BackgroundTask.updated_at < cutoff)
        stmt = stmt.order_by(BackgroundTask.created_at.desc())
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

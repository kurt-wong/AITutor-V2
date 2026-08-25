from decimal import Decimal
from typing import Any
from uuid import UUID

from app.domains.task.repository import BackgroundTaskRepository
from app.models import BackgroundTask


class TaskService:
    def __init__(self, repository: BackgroundTaskRepository) -> None:
        self.repository = repository

    async def create_task(
        self,
        *,
        task_type: str,
        payload: dict[str, Any] | None = None,
    ) -> BackgroundTask:
        task = BackgroundTask(
            task_type=task_type,
            status="queued",
            payload_json=payload,
        )
        return await self.repository.add(task)

    async def start_task(
        self,
        task_id: UUID,
        *,
        stage: str | None = None,
    ) -> BackgroundTask | None:
        task = await self.repository.get(task_id)
        if task is None:
            return None
        task.status = "running"
        task.progress = Decimal("0")
        if stage is not None:
            task.current_stage = stage
        await self.repository.session.flush()
        return task

    async def update_progress(
        self,
        task_id: UUID,
        *,
        progress: float,
        stage: str | None = None,
    ) -> BackgroundTask | None:
        task = await self.repository.get(task_id)
        if task is None:
            return None
        task.progress = Decimal(str(progress))
        if stage is not None:
            task.current_stage = stage
        await self.repository.session.flush()
        return task

    async def succeed_task(
        self,
        task_id: UUID,
        *,
        result: dict[str, Any] | None = None,
    ) -> BackgroundTask | None:
        task = await self.repository.get(task_id)
        if task is None:
            return None
        task.status = "succeeded"
        task.progress = Decimal("1")
        task.result_json = result
        await self.repository.session.flush()
        return task

    async def fail_task(
        self,
        task_id: UUID,
        *,
        error_detail: str,
    ) -> BackgroundTask | None:
        task = await self.repository.get(task_id)
        if task is None:
            return None
        task.status = "failed"
        task.error_detail = error_detail
        await self.repository.session.flush()
        return task

    async def get_task(self, task_id: UUID) -> BackgroundTask | None:
        return await self.repository.get(task_id)

    async def rollback(self) -> None:
        """回滚当前 session（清除异常后的 PendingRollbackError 状态）。"""
        await self.repository.session.rollback()

    async def list_tasks(
        self,
        *,
        task_type: str | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[BackgroundTask]:
        return await self.repository.list_by_filters(
            task_type=task_type,
            status=status,
            skip=skip,
            limit=limit,
        )

    async def count_tasks(
        self,
        *,
        task_type: str | None = None,
        status: str | None = None,
    ) -> int:
        return await self.repository.count_by_filters(
            task_type=task_type,
            status=status,
        )

    async def latest_for_document(self, document_id: UUID) -> BackgroundTask | None:
        return await self.repository.latest_for_document(document_id)

    async def retry_task(self, task_id: UUID) -> BackgroundTask | None:
        task = await self.repository.get(task_id)
        if task is None:
            return None
        task.status = "queued"
        task.progress = None
        task.current_stage = None
        task.error_detail = None
        task.result_json = None
        await self.repository.session.flush()
        return task

    async def recover_stale_running_tasks(
        self,
        *,
        task_type: str,
        active_task_id: UUID | None,
        stale_after_seconds: int = 900,
    ) -> list[UUID]:
        """恢复僵尸 running 任务：worker 重启/崩溃遗留的 running 任务
        永远不会被轮询重新拾取（worker 只查 queued）→ 文档卡在 processing。

        2026-08-25 DOCX 批次：英语任务重启前 processing，重启后 worker 只
        拾取 queued → 卡死，需手工改 DB 才恢复。此处自动兜底：
        - running 且非当前 worker 正在处理的任务（active_task_id）；
        - 且 updated_at 距今超过 stale_after_seconds（防误伤刚启动的任务）。
        满足条件 → 重置为 queued（清 progress/stage），由 worker 重新拾取。

        Returns:
            被恢复的任务 id 列表。
        """
        stale_tasks = await self.repository.list_stale_running(
            task_type=task_type,
            active_task_id=active_task_id,
            stale_after_seconds=stale_after_seconds,
        )
        recovered: list[UUID] = []
        for task in stale_tasks:
            task.status = "queued"
            task.progress = None
            task.current_stage = None
            task.error_detail = None
            task.result_json = None
            recovered.append(task.id)
        if recovered:
            await self.repository.session.flush()
        return recovered

    async def refresh(self, task: BackgroundTask) -> BackgroundTask:
        """显式重新加载 ORM 实例属性。

        2026-08-25 P4 修复：onupdate 列（updated_at 等）在 flush 后标记为
        待从 DB 取回（expired），async 路由里 _serialize_task 同步访问触发
        MissingGreenlet。commit 后 refresh 一次，属性即已加载。
        """
        await self.repository.session.refresh(task)
        return task

    async def commit(self) -> None:
        await self.repository.commit()

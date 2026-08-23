"""答案提取重试队列 Repository。"""

from uuid import UUID

from sqlalchemy import select

from app.models import AnswerExtractionRetry
from app.repositories.base import BaseRepository


class AnswerExtractionRetryRepository(BaseRepository[AnswerExtractionRetry]):
    model = AnswerExtractionRetry

    async def list_pending(self, *, limit: int = 10) -> list[AnswerExtractionRetry]:
        """获取待重试的记录（pending 且未超过最大重试次数）。"""
        stmt = (
            select(AnswerExtractionRetry)
            .where(AnswerExtractionRetry.status == "pending")
            .where(AnswerExtractionRetry.retry_count < AnswerExtractionRetry.max_retries)
            .order_by(AnswerExtractionRetry.created_at.asc())
            .limit(limit)
        )
        result = await self.session.scalars(stmt)
        return list(result)

    async def mark_retrying(self, retry_id: UUID) -> AnswerExtractionRetry | None:
        """标记为重试中。"""
        item = await self.get(retry_id)
        if item is None:
            return None
        item.status = "retrying"
        item.retry_count += 1
        from datetime import datetime, timezone
        item.last_retry_at = datetime.now(timezone.utc)
        await self.session.flush()
        return item

    async def mark_succeeded(self, retry_id: UUID) -> AnswerExtractionRetry | None:
        """标记为成功。"""
        item = await self.get(retry_id)
        if item is None:
            return None
        item.status = "succeeded"
        await self.session.flush()
        return item

    async def mark_failed(self, retry_id: UUID, error: str) -> AnswerExtractionRetry | None:
        """标记为最终失败（超过最大重试次数）。"""
        item = await self.get(retry_id)
        if item is None:
            return None
        item.status = "failed"
        item.error_detail = error[:500]
        await self.session.flush()
        return item

    async def mark_pending(self, retry_id: UUID, error: str) -> AnswerExtractionRetry | None:
        """重试失败后恢复为 pending，保留 retry_count 供下一次轮询继续。"""
        item = await self.get(retry_id)
        if item is None:
            return None
        item.status = "pending"
        item.error_detail = error[:500]
        await self.session.flush()
        return item

    async def reset_to_pending(self, retry_id: UUID) -> AnswerExtractionRetry | None:
        """人工重试：重置为 pending。"""
        item = await self.get(retry_id)
        if item is None:
            return None
        item.status = "pending"
        item.retry_count = 0
        item.error_detail = None
        await self.session.flush()
        return item

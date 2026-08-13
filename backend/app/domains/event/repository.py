from sqlalchemy import select

from app.models import DomainEvent
from app.repositories.base import BaseRepository


class DomainEventRepository(BaseRepository[DomainEvent]):
    model = DomainEvent

    async def list_pending(self, *, limit: int = 100) -> list[DomainEvent]:
        stmt = (
            select(DomainEvent)
            .where(DomainEvent.processed_at.is_(None))
            .order_by(DomainEvent.created_at)
            .limit(limit)
        )
        result = await self.session.scalars(stmt)
        return list(result)

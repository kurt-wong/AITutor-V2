from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.domains.event.repository import DomainEventRepository
from app.models import DomainEvent


class EventService:
    def __init__(self, repository: DomainEventRepository) -> None:
        self.repository = repository

    async def publish(
        self,
        *,
        event_type: str,
        entity_type: str,
        entity_id: UUID | None = None,
        payload: dict[str, Any] | None = None,
    ) -> DomainEvent:
        event = DomainEvent(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            payload_json=payload,
        )
        return await self.repository.add(event)

    async def consume_pending(
        self,
        consumer: Callable[[DomainEvent], Awaitable[None]],
        *,
        limit: int = 100,
    ) -> int:
        events = await self.repository.list_pending(limit=limit)
        for event in events:
            await consumer(event)
            event.processed_at = datetime.now(timezone.utc)
        await self.repository.session.flush()
        return len(events)

    async def commit(self) -> None:
        await self.repository.commit()

from app.models import DomainEvent
from app.repositories.base import BaseRepository


class DomainEventRepository(BaseRepository[DomainEvent]):
    model = DomainEvent

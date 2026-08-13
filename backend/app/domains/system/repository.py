from app.models import SystemConfig
from app.repositories.base import BaseRepository


class SystemConfigRepository(BaseRepository[SystemConfig]):
    model = SystemConfig

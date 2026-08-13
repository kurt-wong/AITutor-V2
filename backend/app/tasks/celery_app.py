from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "aitutors",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    accept_content=["json"],
    task_serializer="json",
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
)


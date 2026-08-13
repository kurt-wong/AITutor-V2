import asyncio

import redis.asyncio as redis
from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine
from app.core.response import build_response
from app.infrastructure.storage import MinIOStorage

router = APIRouter()


@router.get("/health")
def health_check() -> dict:
    return build_response(
        {
            "status": "ok",
            "environment": settings.app_env,
        }
    )


@router.get("/health/dependencies")
async def dependency_health_check() -> dict:
    checks = {
        "postgresql": await _check_postgresql(),
        "redis": await _check_redis(),
        "minio": await _check_minio(),
    }
    status = "ok" if all(item["status"] == "ok" for item in checks.values()) else "degraded"
    return build_response(
        {
            "status": status,
            "dependencies": checks,
        }
    )


async def _check_postgresql() -> dict:
    try:
        async with asyncio.timeout(3):
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        return {"status": "ok", "message": None}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


async def _check_redis() -> dict:
    client = redis.from_url(settings.redis_url)
    try:
        async with asyncio.timeout(3):
            await client.ping()
        return {"status": "ok", "message": None}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}
    finally:
        await client.aclose()


async def _check_minio() -> dict:
    storage = MinIOStorage()
    try:
        async with asyncio.timeout(3):
            ok = await asyncio.to_thread(storage.health_check)
        if ok:
            return {"status": "ok", "message": None}
        return {"status": "error", "message": "MinIO bucket unavailable"}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}

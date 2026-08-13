from fastapi import APIRouter

from app.api.routes import documents, health, tasks

api_router = APIRouter()
api_router.include_router(health.router, prefix="/api", tags=["health"])
api_router.include_router(documents.router, tags=["admin documents"])
api_router.include_router(tasks.router, tags=["tasks"])

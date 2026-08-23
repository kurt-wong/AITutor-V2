from fastapi import APIRouter

from app.api.routes import documents, health, questions, tasks

api_router = APIRouter()
api_router.include_router(health.router, prefix="/api", tags=["health"])
api_router.include_router(documents.router, tags=["admin documents"])
api_router.include_router(tasks.router, tags=["tasks"])
api_router.include_router(questions.router, tags=["admin questions"])

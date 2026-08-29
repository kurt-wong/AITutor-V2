from fastapi import APIRouter, Depends

from app.api.dependencies import verify_admin_key
from app.api.routes import documents, health, questions, question_types, tasks

api_router = APIRouter()
api_router.include_router(health.router, prefix="/api", tags=["health"])
api_router.include_router(documents.router, tags=["admin documents"], dependencies=[Depends(verify_admin_key)])
api_router.include_router(tasks.router, tags=["tasks"])
api_router.include_router(questions.router, tags=["admin questions"], dependencies=[Depends(verify_admin_key)])
api_router.include_router(question_types.router, tags=["question-types"], dependencies=[Depends(verify_admin_key)])

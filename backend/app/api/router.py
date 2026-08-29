from fastapi import APIRouter, Depends

from app.api.dependencies import verify_admin_key
from app.api.routes import documents, health, questions, question_types, tasks

# 注册路由
# 以下域有表模型+service 但尚无 API 路由（未来功能骨架）：
# - analytics（统计分析增强）
# - generation（AI 组题，目标 3）
# - student（练习与判分，目标 5）
# - wrong_question（错题本，目标 4）
# - auth（认证系统）
# - system（系统配置）

api_router = APIRouter()
api_router.include_router(health.router, prefix="/api", tags=["health"])
api_router.include_router(documents.router, tags=["admin documents"], dependencies=[Depends(verify_admin_key)])
api_router.include_router(tasks.router, tags=["tasks"], dependencies=[Depends(verify_admin_key)])
api_router.include_router(questions.router, tags=["admin questions"], dependencies=[Depends(verify_admin_key)])
api_router.include_router(question_types.router, tags=["question-types"], dependencies=[Depends(verify_admin_key)])

from fastapi import APIRouter, Depends

from app.api.dependencies import verify_admin_key
from app.api.routes import documents, health, questions, question_types, tasks

# 注册路由
# 以下域尚无 API 路由（未来功能骨架，占位域）：
# - analytics：空 __init__.py，无表模型/service（统计分析增强）
# - embedding：仅 QuestionEmbedding 表，无 service（向量检索）
# - generation：表+repository+service 骨架完整（AI 组题，目标 3）
# - student：表+repository+service 骨架完整（练习与判分，目标 5）
# - wrong_question：表+repository+service 骨架完整（错题本，目标 4）
# - system：表+repository，无 service（系统配置）
# auth 域：表+repository 已有，verify_admin_key 已激活（见上方 dependencies）

api_router = APIRouter()
api_router.include_router(health.router, prefix="/api", tags=["health"])
api_router.include_router(documents.router, tags=["admin documents"], dependencies=[Depends(verify_admin_key)])
api_router.include_router(tasks.router, tags=["tasks"], dependencies=[Depends(verify_admin_key)])
api_router.include_router(questions.router, tags=["admin questions"], dependencies=[Depends(verify_admin_key)])
api_router.include_router(question_types.router, tags=["question-types"], dependencies=[Depends(verify_admin_key)])

import asyncio
import logging
from contextlib import asynccontextmanager

import app.core.logging  # noqa: F401  # 触发 root logger INFO 配置（worker 日志可见）

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.context import finish_request, get_request_id, start_request
from app.core.response import build_response

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: start background worker on startup."""
    from app.core.database import async_session_factory
    from app.domains.document.processor import DocumentProcessor
    from app.domains.document.repository import DocumentRepository, DocumentProcessingLogRepository
    from app.domains.document.service import DocumentService
    from app.domains.task.service import TaskService
    from app.domains.task.repository import BackgroundTaskRepository
    from app.infrastructure.storage import MinIOStorage
    from app.ai.gateway import get_llm_gateway
    from app.worker.document_worker import document_parse_worker

    stop_event = asyncio.Event()

    # 创建真实依赖（无状态，可共享）
    storage = MinIOStorage()
    gateway = get_llm_gateway()  # 使用已构建的 gateway（含 providers）

    # Worker 内部每次任务创建新 session，避免内存泄漏
    async def create_task_services():
        """每次任务创建新的 service 实例（独立 session）。"""
        session = async_session_factory()
        task_repo = BackgroundTaskRepository(session)
        doc_repo = DocumentRepository(session)
        log_repo = DocumentProcessingLogRepository(session)
        return session, TaskService(task_repo), DocumentService(doc_repo, log_repo)

    worker_task = asyncio.create_task(
        document_parse_worker(
            storage=storage,
            gateway=gateway,
            create_task_services=create_task_services,
            stop_event=stop_event,
        )
    )
    logger.info("Background worker started")

    yield

    # 关闭
    stop_event.set()
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass
    logger.info("Background worker stopped")

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.middleware("http")
async def add_request_context(request: Request, call_next):
    tokens = start_request()
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = get_request_id()
        return response
    finally:
        finish_request(tokens)


# P4E: serve frontend dist from backend so user can access UI at localhost:8000
from pathlib import Path as _Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

_frontend_dist = _Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _frontend_dist.is_dir():
    app.mount("/assets", StaticFiles(directory=str(_frontend_dist / "assets")), name="frontend-assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """SPA catch-all: serve frontend dist files, fallback to index.html for client-side routing.

        Note: /api/* and /docs routes are registered before this catch-all, so they take precedence.
        """
        # Try to serve exact file first (favicon, manifest, etc.)
        file_path = _frontend_dist / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        # SPA fallback: serve index.html for all non-file routes
        return FileResponse(str(_frontend_dist / "index.html"))

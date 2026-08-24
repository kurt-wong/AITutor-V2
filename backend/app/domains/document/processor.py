"""
文档处理服务 — 将 Pipeline 与 Background Task 集成。

负责：
1. 从 MinIO 下载 PDF
2. 执行 Pipeline（含进度回调）
3. LLM 答案提取
4. 入库（questions / question_instances / question_images）
5. 将结果保存到 BackgroundTask.result_json
6. 更新文档处理状态

详见 Docs/01_Product/T3_IMPLEMENTATION.md §9 Task 2.4。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.gateway import LLMGateway
from app.domains.document.answer_extractor import extract_answers_from_markdown
from app.domains.document.ingestion import IngestionResult, ingest_pipeline_result
from app.domains.document.simple_pipeline import run_simple_pipeline
from app.domains.document.pipeline import PipelineResult, save_result
from app.models import Document
from app.domains.task.service import TaskService
from app.infrastructure.storage import MinIOStorage

logger = logging.getLogger(__name__)
_WORKSPACE_TMP = Path(__file__).resolve().parents[4] / "tmp"


class DocumentProcessor:
    """文档处理器：Pipeline + Background Task 集成。"""

    def __init__(
        self,
        task_service: TaskService,
        storage: MinIOStorage,
        gateway: LLMGateway,
    ) -> None:
        self.task_service = task_service
        self.storage = storage
        self.gateway = gateway

    async def process_document(
        self,
        task_id: UUID,
        document_id: UUID,
        object_key: str,
        filename: str,
    ) -> PipelineResult:
        """处理单个文档。

        Args:
            task_id: Background Task ID
            document_id: 文档 ID
            object_key: MinIO 对象键
            filename: 文件名

        Returns:
            PipelineResult: 管线执行结果
        """
        # 1. 启动任务
        await self.task_service.start_task(task_id, stage="downloading")
        await self.task_service.commit()

        # 2. 下载 PDF 到临时目录
        try:
            pdf_path = await self._download_pdf(object_key, filename)
            await self.task_service.update_progress(task_id, progress=0.1, stage="downloaded")
            await self.task_service.commit()
        except Exception as exc:
            await self.task_service.fail_task(task_id, error_detail=f"下载失败: {exc}")
            raise

        # 3. 执行 Pipeline
        try:
            await self.task_service.update_progress(task_id, progress=0.2, stage="parsing")
            await self.task_service.commit()

            progress_cb = self.get_progress_callback(task_id)
            result = await run_simple_pipeline(
                pdf_path=pdf_path,
                filename=filename,
                gateway=self.gateway,
                progress_callback=progress_cb,
            )

            # 4. 根据管线结果状态决定任务状态（C5/C6 修复）
            # 不在此处 commit — 由 worker 统一提交 task + document（H3 修复）
            if result.status == "failed":
                # 优先取 result.errors（含 ocr_unavailable 等语义标记，2026-08-25：
                # paddle 不可用时 simple_pipeline 标记 ocr_unavailable 供批量恢复识别）
                error_msg = "; ".join(result.errors) if result.errors else (
                    result.stage_errors[0]["error"] if result.stage_errors else "pipeline failed"
                )
                await self.task_service.fail_task(
                    task_id,
                    error_detail=f"解析失败: {error_msg}",
                )
                logger.error(
                    "document_failed document_id=%s task_id=%s errors=%s",
                    document_id, task_id, result.errors,
                )
            elif result.status == "partial_failed":
                # fail closed：partial_failed 当前未启用，按 failed 处理
                error_msg = "partial_failed: " + ("; ".join(result.errors) if result.errors else "incomplete processing")
                await self.task_service.fail_task(
                    task_id,
                    error_detail=f"解析失败: {error_msg}",
                )
                logger.error(
                    "document_partial_failed document_id=%s task_id=%s errors=%s",
                    document_id, task_id, result.errors,
                )
            else:
                await self.task_service.succeed_task(
                    task_id,
                    result=result.to_dict(),
                )
                logger.info(
                    "document_processed document_id=%s task_id=%s questions=%d",
                    document_id, task_id, len(result.sliced_questions),
                )

            return result

        except Exception as exc:
            # P0-A 修复（2026-08-23）：异常后 session 可能被毒化（PendingRollbackError），
            # 必须先 rollback 清除失败态，否则 fail_task 的 repository.get 也会失败，
            # 任务永远卡在 running。
            try:
                await self.task_service.rollback()
            except Exception:
                pass
            await self.task_service.fail_task(task_id, error_detail=f"解析失败: {exc}")
            raise
        finally:
            # 清理临时文件（下载失败时 pdf_path 可能未定义）
            import shutil
            try:
                tmp_dir = pdf_path.parent
                if tmp_dir.exists() and tmp_dir.name.startswith("aitutors_"):
                    shutil.rmtree(tmp_dir, ignore_errors=True)
            except NameError:
                pass  # pdf_path 未赋值（下载阶段失败）

    async def _download_pdf(self, object_key: str, filename: str) -> Path:
        """从 MinIO 下载 PDF 到临时目录。

        注意：不用 tempfile.mkdtemp —— 其 mode=0o700 在沙箱环境下创建的
        子目录 ACL 只授予沙箱 SID，后续写入被拒（WinError 5/Errno 13）。
        改用 Path.mkdir 继承工作区 tmp 的可写 ACL + uuid 唯一目录名。
        """
        import asyncio
        import uuid

        _WORKSPACE_TMP.mkdir(parents=True, exist_ok=True)
        tmp_dir = _WORKSPACE_TMP / f"aitutors_{uuid.uuid4().hex[:8]}"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = tmp_dir / filename

        # 下载文件（使用线程池避免阻塞事件循环）
        data = await asyncio.to_thread(self.storage.get_object, object_key)
        await asyncio.to_thread(pdf_path.write_bytes, data)

        return pdf_path

    def get_progress_callback(self, task_id: UUID):
        """创建进度回调函数，用于 Pipeline 内部更新进度。"""

        async def callback(stage: str, progress: float):
            await self.task_service.update_progress(
                task_id, progress=progress, stage=stage
            )
            await self.task_service.commit()

        return callback

    async def extract_and_ingest(
        self,
        *,
        session: AsyncSession,
        pipeline_result: PipelineResult,
        document: Document,
        l1_markdown: str | None = None,
    ) -> IngestionResult:
        """管线成功后，提取答案并入库。

        流程：
        1. 从 L1 markdown 中提取答案（LLM）
        2. 将管线结果 + 答案合并后写入数据库

        Args:
            session: 数据库会话
            pipeline_result: 管线输出结果
            document: 来源文档记录
            l1_markdown: OCR markdown 全文（用于 LLM 答案提取）

        Returns:
            IngestionResult
        """
        from app.models import Document

        # 1. LLM 答案提取
        answer_result = None
        answer_extraction_status = "skipped"  # skipped / success / failed / exception

        if l1_markdown:
            try:
                answer_result = await extract_answers_from_markdown(
                    l1_markdown,
                    gateway=self.gateway,
                    filename=document.filename,
                )
                if answer_result.ok:
                    answer_extraction_status = "success"
                    logger.info(
                        "answer_extraction: subject=%s total=%d verified=%d",
                        answer_result.subject,
                        answer_result.total,
                        answer_result.verified_count,
                    )
                else:
                    answer_extraction_status = "failed"
                    logger.warning("answer_extraction failed: %s", answer_result.error)
            except Exception as exc:
                answer_extraction_status = "exception"
                logger.warning("answer_extraction exception: %s", exc)

        # 2. 入库（传入 gateway 用于 LLM 相似题目判断）
        ingestion_result = await ingest_pipeline_result(
            session,
            pipeline_result=pipeline_result,
            answer_result=answer_result,
            document=document,
            gateway=self.gateway,
        )

        # 3. 记录答案提取状态到入库结果（供 worker 写入 task result）
        ingestion_result.answer_extraction_status = answer_extraction_status
        ingestion_result.answer_extraction_error = (
            answer_result.error if answer_result and answer_result.error else None
        )

        return ingestion_result

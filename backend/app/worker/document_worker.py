"""Document parse worker — polls for queued tasks and processes them.

本地部署轮询模式：每 N 秒检查一次 queued 任务，顺序执行。
无需 Redis/RabbitMQ 等外部依赖。

详见 Docs/01_Product/T3_IMPLEMENTATION.md §9 Task 2.4。
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import Any
from uuid import UUID

from sqlalchemy import func, select

from app.infrastructure.storage import MinIOStorage
from app.ai.gateway import LLMGateway

logger = logging.getLogger(__name__)

# 轮询间隔（秒）
_POLL_INTERVAL = 5

# 2026-08-25 P7/P10 修复：任务级超时兜底（秒）。
# worker 内 LLM 请求挂死（deepseek 正常但请求无限等待）时，LLM 层
# asyncio.wait_for 会在 ~10min 后取消请求并重试/失败，但为避免任何
# 未覆盖环节卡死整个批次，processor.process_document 整体再加一层
# 超时：超时后任务标记 failed（可重试，P4 已修复 retry）。
_TASK_TIMEOUT_SECONDS = 3600


async def document_parse_worker(
    *,
    storage: MinIOStorage,
    gateway: LLMGateway,
    create_task_services: Callable[(), Coroutine[Any, Any, tuple]],
    stop_event: asyncio.Event | None = None,
) -> None:
    """后台轮询 worker：消费 document_parse 任务。

    每次任务创建独立 session，避免内存泄漏。

    Args:
        storage: MinIO 存储
        gateway: LLM 网关
        create_task_services: 创建 (session, task_service, document_service) 的工厂函数
        stop_event: 停止信号（用于优雅关闭）
    """
    from app.domains.document.processor import DocumentProcessor

    stop = stop_event or asyncio.Event()
    logger.info("document_parse_worker started (poll_interval=%ds)", _POLL_INTERVAL)

    # 2026-08-25 僵尸任务恢复：worker 重启/崩溃后遗留的 running 任务
    # 不会被轮询重新拾取（只查 queued）。每次轮询先恢复「超时未更新的
    # running 任务」（排除当前正在处理的任务），避免文档永久卡 processing。
    _active_task_id: UUID | None = None

    while not stop.is_set():
        session = None
        task = None
        task_service = None
        try:
            # 每次任务创建新的 service 实例（独立 session）
            session, task_service, document_service = await create_task_services()

            # 僵尸恢复（幂等）：running 且 updated_at 超时、非当前处理中 →
            # 重置 queued，由下方轮询重新拾取。
            try:
                recovered = await task_service.recover_stale_running_tasks(
                    task_type="document_parse",
                    active_task_id=_active_task_id,
                )
                if recovered:
                    logger.warning(
                        "worker: recovered %d stale running task(s): %s",
                        len(recovered),
                        [str(t) for t in recovered],
                    )
                    await task_service.commit()
            except Exception:
                logger.exception("worker: recover_stale_running_tasks failed")
                await task_service.rollback()

            # 查询 queued 状态的 document_parse 任务
            tasks = await task_service.list_tasks(
                task_type="document_parse",
                status="queued",
                skip=0,
                limit=1,
            )
            if not tasks:
                await asyncio.sleep(_POLL_INTERVAL)
                continue

            task = tasks[0]
            _active_task_id = task.id
            document_id = UUID(task.payload_json["document_id"])
            # 2026-08-25：显式 OCR 模型覆盖（上传时可选传入，如语文 VL 重跑）
            ocr_model = (task.payload_json or {}).get("ocr_model") or None
            logger.info("worker: picked up task %s for document %s", task.id, document_id)

            # 从 DB 获取 document 信息
            document = await document_service.get_document(document_id)
            if document is None:
                await task_service.fail_task(task.id, error_detail=f"Document {document_id} not found")
                await task_service.commit()
                continue

            # 更新文档状态为 processing
            document.processing_status = "processing"
            await document_service.commit()

            # 创建 processor（使用当前 session 的 services）
            processor = DocumentProcessor(
                task_service=task_service, storage=storage, gateway=gateway
            )

            try:
                # P7/P10 修复：任务级超时兜底——任何环节（LLM/OCR/入库）
                # 挂死超 _TASK_TIMEOUT_SECONDS 即取消并走外层 except 标记
                # failed（可重试），避免单任务无限卡住阻塞整个批次。
                result = await asyncio.wait_for(
                    processor.process_document(
                        task_id=task.id,
                        document_id=document_id,
                        object_key=document.object_key,
                        filename=document.filename,
                        subject=document.subject,
                        ocr_model=ocr_model,
                    ),
                    timeout=_TASK_TIMEOUT_SECONDS,
                )

                # C5/C6: 根据 result.status 设置 document 状态
                # processor 内部已调用 succeed_task/fail_task（但不 commit）
                # worker 统一提交 task + document（H3 原子提交）
                if result.status == "succeeded":
                    # 管线成功 → 存储三份 markdown → 提取答案并入库
                    try:
                        # 构建 OCR-MARKDOWN（LLM 标注前的原始 L1）
                        ocr_markdown = None
                        if result.l1_document:
                            ocr_markdown = "\n".join(line.text for line in result.l1_document.lines)

                        # 构建 native markdown（PyMuPDF 提取的，图片bbox/答案表/上下标辅助）
                        native_markdown = None
                        if result.native_l1_document:
                            native_markdown = "\n".join(line.text for line in result.native_l1_document.lines)

                        # 构建 LLM 批注版（包含完整 L2 标注信息，JSON 格式）
                        # Phase 2A Step 3 + Phase 2C：完整 L2 字段 + structure_signature + annotation_version
                        llm_annotated = None
                        if result.l2_annotation:
                            import json as _json
                            annotated_data = _serialize_l2_for_persistence(result.l2_annotation)
                            llm_annotated = _json.dumps(annotated_data, ensure_ascii=False, indent=2)

                        # 存入 document 表（三份持久化）
                        document.native_markdown = native_markdown
                        document.ocr_markdown = ocr_markdown
                        document.llm_annotated_markdown = llm_annotated

                        # Phase 2A Step 3：幂等重跑清理 — 只清理该文档下
                        # source_type='document' 且未被人工审核（status='reviewing'）的记录；
                        # 已审核/已修正（review_overrides 非空）的记录保留，不静默覆盖
                        await _cleanup_unreviewed_records(session, document_id)

                        # 提取答案并入库
                        ingestion_result = await processor.extract_and_ingest(
                            session=session,
                            pipeline_result=result,
                            document=document,
                            l1_markdown=ocr_markdown,
                        )
                        logger.info(
                            "ingestion: document_id=%s ingested=%d skipped=%d failed=%d answer_extraction=%s",
                            document_id,
                            ingestion_result.ingested,
                            ingestion_result.skipped,
                            ingestion_result.failed,
                            ingestion_result.answer_extraction_status,
                        )

                        # 如果答案提取失败，写入重试队列
                        if ingestion_result.answer_extraction_status in ("failed", "exception"):
                            from app.models import AnswerExtractionRetry, DocumentProcessingLog
                            # 写入重试表
                            session.add(AnswerExtractionRetry(
                                document_id=document_id,
                                task_id=task.id,
                                error_detail=ingestion_result.answer_extraction_error or "unknown error",
                                status="pending",
                            ))
                            # 同时写入处理日志（兼容旧逻辑）
                            session.add(DocumentProcessingLog(
                                document_id=document_id,
                                stage="answer_extraction_failed",
                                message=ingestion_result.answer_extraction_error or "unknown error",
                            ))

                        task_result = result.to_dict()
                        task_result["ingestion"] = ingestion_result.to_dict()
                        await task_service.succeed_task(task.id, result=task_result)

                        # Phase 2A Step 3：ingestion 真正完成才标记 document completed；
                        # 异常路径在下方 except 中标记 failed，不再把失败当成功
                        document.processing_status = "completed"
                    except Exception as exc:
                        # Phase 2A Step 3 + P1-D：ingestion 异常 → task failed + document failed
                        # （答案提取失败不在此路径：extract_and_ingest 内部捕获，走 retry queue）
                        # P0-A: session 可能被 UniqueViolationError 毒化（PendingRollbackError），
                        # 必须先 rollback 清除失败态，否则后续 fail_task/mark_failed 也会失败。
                        logger.exception("ingestion failed for document %s", document_id)
                        ingestion_error = f"ingestion failed: {type(exc).__name__}: {exc}"[:500]
                        try:
                            await session.rollback()
                        except Exception:
                            logger.debug("worker: session rollback after ingestion error (expected if savepoint handled)")
                        try:
                            await task_service.fail_task(
                                task.id,
                                error_detail=ingestion_error,
                            )
                        except Exception:
                            logger.exception("worker: failed to mark task as failed after ingestion error")
                        document.processing_status = "failed"
                        document.error_message = ingestion_error
                elif result.status == "failed":
                    document.processing_status = "failed"
                    error_msg = "; ".join(result.errors) if result.errors else "pipeline failed"
                    document.error_message = error_msg[:500]
                elif result.status == "scanned":
                    # 2026-08-25 扫描件标注：纯扫描 PDF（无文本层）OCR 不可靠，
                    # 标记 scanned 供后续集中处理，不入库、不重试。
                    document.processing_status = "scanned"
                    error_msg = "; ".join(result.errors) if result.errors else "scanned pdf"
                    document.error_message = error_msg[:500]
                elif result.status == "partial_failed":
                    logger.error(
                        "partial_failed task_id=%s document_id=%s errors=%s",
                        task.id, document_id, result.errors,
                    )
                    document.processing_status = "failed"
                    error_msg = "; ".join(result.errors) if result.errors else "partial_failed"
                    document.error_message = error_msg[:500]
                else:
                    document.processing_status = "completed"

                # H3: 最终提交 — task 状态由 processor 设置，document 状态由 worker 设置
                try:
                    await document_service.commit()
                except Exception:
                    logger.exception("worker: final commit failed for task %s, rolling back", task.id)
                    try:
                        await session.rollback()
                    except Exception:
                        logger.exception("worker: rollback also failed for task %s", task.id)
                    # 不继续用脏 session
                    return

                if result.errors:
                    logger.warning("worker: task %s completed with errors: %s", task.id, result.errors)

            except Exception as exc:
                # 处理失败：更新文档状态
                # P0-A: session 可能被毒化，先 rollback 再尝试写入
                logger.exception("worker: processing failed for task %s", task.id)
                try:
                    await session.rollback()
                except Exception:
                    logger.debug("worker: rollback in outer except (expected if savepoint handled)")
                document.processing_status = "failed"
                # P7/P10 修复：任务级超时（asyncio.wait_for 取消 process_document）
                # 时 task 停在 running，需在此标记 failed（幂等），否则僵尸任务
                # 永久阻塞该文档重试。
                document.error_message = str(exc)[:500]  # 截断避免超长
                try:
                    current_task = await task_service.get_task(task.id)
                    if current_task is not None and current_task.status == "running":
                        timeout_hint = "task timeout" if isinstance(exc, asyncio.TimeoutError) else "processing failed"
                        await task_service.fail_task(task.id, error_detail=f"{timeout_hint}: {exc}"[:500])
                except Exception:
                    logger.exception("worker: failed to mark task as failed after processing error")
                try:
                    await document_service.commit()
                except Exception:
                    logger.exception("worker: except-path commit failed for task %s, rolling back", task.id)
                    try:
                        await session.rollback()
                    except Exception:
                        pass

        except Exception:
            logger.exception("worker: unexpected error in poll cycle")
            # 幂等 fail：仅当任务尚未被标记为 failed 时才操作（H5 修复）
            try:
                if task is not None and task_service is not None:
                    current = await task_service.get_task(task.id)
                    if current is not None and current.status != "failed":
                        await task_service.fail_task(task.id, error_detail="Worker unexpected error")
                        await task_service.commit()
            except Exception:
                logger.exception("worker: failed to mark task as failed")
        finally:
            # 关闭 session，释放连接
            if session is not None:
                try:
                    await session.close()
                except Exception:
                    pass
            # 当前任务已结束（成功/失败/异常），下一轮可恢复该 id 的僵尸状态
            _active_task_id = None
            await asyncio.sleep(_POLL_INTERVAL)

    logger.info("document_parse_worker stopped")


def _serialize_l2_for_persistence(l2_annotation) -> dict:
    """将 L2 Document Annotation 序列化为持久化 JSON（llm_annotated_markdown）。

    Phase 2A Step 3：保留 knowledge_points/difficulty/score/corrected_anchors/
    anchor_status/question_type/sub_questions 等完整 L2 字段。
    Phase 2C：写入 annotation_version（prompt 版本）+ structure_signature（每题）。
    """
    from app.domains.document.line_annotator import ANNOTATION_PROMPT_VERSION

    l2 = l2_annotation

    def _serialize_signature(q) -> dict | None:
        """Phase 2C：structure_signature 附带上 source/confidence/annotation_version 元数据。

        PLAN §5.2：LLM 输出的 structure_signature 需要保留来源、置信度、版本，
        用于后续数据可比性（prompt 版本变化后能区分数据来自哪个版本）。

        语义说明（对抗性审查 F6）：`confidence` 复用题目级标注置信度
        （L2QuestionAnnotation.confidence），是 LLM 对整题标注的确信程度，
        非独立输出的 signature 置信度（prompt 未单独要求 LLM 输出 signature 置信度）。
        """
        sig = q.structure_signature
        if not sig:
            return None
        enriched = dict(sig)
        enriched["source"] = "llm"
        enriched["annotation_version"] = ANNOTATION_PROMPT_VERSION
        enriched["confidence"] = q.confidence
        return enriched

    return {
        "filename": l2.filename,
        "subject": l2.subject,
        "grade": l2.grade,
        "year": l2.year,
        "school": l2.school,
        "annotation_version": ANNOTATION_PROMPT_VERSION,
        "metadata_confidence": l2.metadata_confidence,
        "warnings": l2.warnings,
        "anchor_status_summary": l2.anchor_status_summary,
        "corrected_anchors": [
            {
                "field": a.field,
                "llm_line_ids": a.llm_line_ids,
                "corrected_line_ids": a.corrected_line_ids,
                "anchor_status": a.anchor_status,
                "validation_passed": a.validation_passed,
                "evidence": a.evidence,
                "question_number": a.question_number,
            }
            for a in l2.corrected_anchors
        ],
        "questions": [
            {
                "question_number": q.question_number,
                "question_type": q.question_type,
                "section_id": q.section_id,
                "stem_line_ids": q.stem_line_ids,
                "options_line_ids": q.options_line_ids,
                "answer": q.answer,
                "answer_line_ids": q.answer_line_ids,
                "explanation_line_ids": q.explanation_line_ids,
                "difficulty": q.difficulty,
                "score": q.score,
                "knowledge_points": q.knowledge_points,
                "confidence": q.confidence,
                "source_page": q.source_page,
                "is_composite": q.is_composite,
                "shared_material_line_ids": q.shared_material_line_ids,
                "stem_start_marker": q.stem_start_marker,
                "stem_end_marker": q.stem_end_marker,
                "structure_signature": _serialize_signature(q),
                "sub_questions": [
                    {
                        "qno": s.qno,
                        "question_type": s.question_type,
                        "answer": s.answer,
                        "knowledge_points": s.knowledge_points,
                        "score": s.score,
                        # P4E.1（2026-08-27）：L2 落盘补子题行号 + 切片文本
                        # （此前丢失，LOG v6.43 链路断裂 #4）。
                        "stem_line_ids": getattr(s, "stem_line_ids", None) or [],
                        "options_line_ids": getattr(s, "options_line_ids", None) or {},
                        "stem": getattr(s, "stem", "") or "",
                        "options": getattr(s, "options", None) or [],
                    }
                    for s in (q.sub_questions or [])
                ],
            }
            for q in l2.questions
        ],
    }


async def _cleanup_unreviewed_records(session, document_id: UUID) -> None:
    """幂等重跑清理：删除该文档下未审核的 document 来源记录。

    Phase 2A Step 3（PLAN §7.1 Step 3 / docs_archive/2026-08-24/PHASE_2A_EXECUTION_PLAN.md Step 3）：
    - 只清理 `source_type='document'` 且 `status='reviewing'`（未被人工审核）的记录；
    - 已审核（status != 'reviewing'）或 review_overrides 非空的记录保留，不静默覆盖。
    - 只删除当前 document_id 下的 Instance；同一 Question 在其他文档下的 Instance 保留。
    - 仅当 Question 不再有剩余 Instance 时才删除 Question 及其 FK 依赖。

    注意：调用方会在同一事务内继续 ingestion，本函数不自行 commit。
    """
    from app.models import Question, QuestionInstance

    # 找出该文档下未审核的 instance
    stmt = (
        select(QuestionInstance)
        .join(Question, Question.id == QuestionInstance.question_id)
        .where(QuestionInstance.document_id == document_id)
        .where(QuestionInstance.source_type == "document")
        .where(Question.status == "reviewing")
    )
    instances = list(await session.scalars(stmt))
    if not instances:
        return

    # 只删除当前 document 下的 instance（不碰其他文档的 instance）
    question_ids = {i.question_id for i in instances}
    for inst in instances:
        await session.delete(inst)
    await session.flush()

    # 对每个受影响的 Question，检查是否还有剩余 Instance
    from app.models import QuestionImage, QuestionKnowledge, QuestionEmbedding
    deleted_questions = 0
    updated_questions = 0
    for qid in question_ids:
        remaining = await session.scalar(
            select(func.count()).select_from(QuestionInstance)
            .where(QuestionInstance.question_id == qid)
        )
        if remaining == 0:
            # 无剩余 Instance → 删除 FK 依赖 + 删除 Question
            for model_cls in (QuestionImage, QuestionKnowledge, QuestionEmbedding):
                records = list(await session.scalars(
                    select(model_cls).where(model_cls.question_id == qid)
                ))
                for r in records:
                    await session.delete(r)
            question = await session.get(Question, qid)
            if question is not None:
                await session.delete(question)
            deleted_questions += 1
        else:
            # 还有其他文档的 Instance → 更新 occurrence_count，保留 Question
            question = await session.get(Question, qid)
            if question is not None:
                question.occurrence_count = remaining
            updated_questions += 1
    await session.flush()
    logger.info(
        "rerun cleanup: document_id=%s removed %d unreviewed instance(s), "
        "deleted %d question(s), updated %d question(s) with remaining instances",
        document_id, len(instances), deleted_questions, updated_questions,
    )

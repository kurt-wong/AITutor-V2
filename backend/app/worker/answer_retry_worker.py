"""答案提取重试 Worker — 定期扫描待重试记录，重新执行答案提取。

本地部署轮询模式：每 N 秒检查一次 pending 记录。
失败的重试会递增 retry_count，超过 max_retries 后标记为 failed。
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import Any

from app.ai.gateway import LLMGateway
from app.domains.document.answer_extractor import extract_answers_from_markdown
from app.domains.document.retry_repository import AnswerExtractionRetryRepository

logger = logging.getLogger(__name__)

# 轮询间隔（秒）
_POLL_INTERVAL = 30


async def answer_retry_worker(
    *,
    gateway: LLMGateway,
    create_session: Callable[[], Coroutine[Any, Any, Any]],
    stop_event: asyncio.Event | None = None,
) -> None:
    """后台轮询 worker：消费答案提取重试队列。

    流程：
    1. 查询 status=pending 且 retry_count < max_retries 的记录
    2. 从 documents 表读取 ocr_markdown
    3. 重新执行 LLM 答案提取
    4. 成功 → 更新 questions 表中的答案，标记 succeeded
    5. 失败 → 递增 retry_count，超过上限标记 failed

    Args:
        gateway: LLM 网关
        create_session: 创建 session 的工厂函数
        stop_event: 停止信号
    """
    stop = stop_event or asyncio.Event()
    logger.info("answer_retry_worker started (poll_interval=%ds)", _POLL_INTERVAL)

    while not stop.is_set():
        session = None
        retry_repo = None
        item = None
        try:
            session = await create_session()
            retry_repo = AnswerExtractionRetryRepository(session)

            pending_items = await retry_repo.list_pending(limit=5)
            if not pending_items:
                await asyncio.sleep(_POLL_INTERVAL)
                continue

            for item in pending_items:
                try:
                    await _process_one_retry(session, retry_repo, item, gateway)
                except Exception as exc:
                    logger.warning("retry processing failed for %s: %s", item.id, exc)
                    await _mark_retry_exception(retry_repo, item, str(exc))

            await session.commit()

        except Exception:
            logger.exception("answer_retry_worker: unexpected error in poll cycle")
            try:
                if session:
                    await session.rollback()
            except Exception:
                pass
        finally:
            if session:
                try:
                    await session.close()
                except Exception:
                    pass
            await asyncio.sleep(_POLL_INTERVAL)

    logger.info("answer_retry_worker stopped")


async def _process_one_retry(
    session,
    retry_repo: AnswerExtractionRetryRepository,
    item,
    gateway: LLMGateway,
) -> None:
    """处理单条重试记录。

    Phase 2A Step 4：答案更新不再按 `source_document_name + 顺序` 猜测题目，
    改为通过 `question_instances(document_id, source_question_number)` 精确定位。
    """
    from app.models import Document
    from app.domains.question.repository import QuestionRepository

    logger.info(
        "retry: processing %s (document=%s, attempt=%d/%d)",
        item.id, item.document_id, item.retry_count + 1, item.max_retries,
    )

    # 标记为重试中
    await retry_repo.mark_retrying(item.id)

    # 读取 ocr_markdown
    document = await session.get(Document, item.document_id)
    if not document or not document.ocr_markdown:
        await retry_repo.mark_failed(item.id, "document or ocr_markdown not found")
        return

    # 重新执行 LLM 答案提取
    try:
        answer_result = await extract_answers_from_markdown(
            document.ocr_markdown,
            gateway=gateway,
            filename=document.filename,
        )
        if not answer_result.ok:
            raise RuntimeError(f"answer extraction failed: {answer_result.error}")
    except Exception as exc:
        # 提取失败不能把记录留在 retrying：未达上限恢复 pending，达到上限标 failed
        logger.warning("retry: answer extraction failed for %s: %s", item.id, exc)
        await _mark_retry_exception(retry_repo, item, str(exc))
        return

    # Phase 2A Step 4：通过 question_instances(document_id, source_question_number) 精确关联
    question_repo = QuestionRepository(session)
    updated = 0
    missing = 0
    for q_num, extracted in answer_result.answers.items():
        if not extracted.answer.strip():
            continue
        question = await question_repo.find_by_document_and_question_number(
            item.document_id,
            str(q_num),
        )
        if question is None:
            # document_id + source_question_number 找不到 Instance：
            # 记录失败而不是更新错误题目
            logger.warning(
                "retry: no instance for document=%s question_number=%s, skip",
                item.document_id, q_num,
            )
            missing += 1
            continue
        # 只填充空答案（不覆盖已有答案，保留人工审核/管线结果）
        if not question.answer or question.answer.strip() == "":
            question.answer = extracted.answer
            question.explanation = extracted.explanation or question.explanation
            updated += 1

    if missing > 0:
        await retry_repo.mark_failed(
            item.id,
            f"{missing} question(s) not found via question_instances(document_id, source_question_number)",
        )
        logger.info("retry: %s marked failed, %d question(s) missing instance", item.id, missing)
        return

    await retry_repo.mark_succeeded(item.id)
    logger.info("retry: succeeded %s, updated %d questions", item.id, updated)


async def _mark_retry_exception(retry_repo, item, error: str) -> None:
    """统一处理重试异常：未超限恢复 pending，超限标记 failed。"""
    if item.retry_count >= item.max_retries:
        await retry_repo.mark_failed(item.id, error)
    else:
        await retry_repo.mark_pending(item.id, error)

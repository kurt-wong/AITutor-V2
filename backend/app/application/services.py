from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from typing import BinaryIO
from uuid import UUID
from uuid import uuid4

from app.domains.document.service import DocumentService
from app.domains.event.service import EventService
from app.domains.question.service import QuestionService
from app.domains.task.service import TaskService
from app.infrastructure.storage import MinIOStorage
from app.models import BackgroundTask, Document, Question


class TaskApplicationService:
    def __init__(
        self,
        task_service: TaskService,
        event_service: EventService,
    ) -> None:
        self.task_service = task_service
        self.event_service = event_service

    async def create_and_queue(
        self,
        *,
        task_type: str,
        payload: dict[str, Any] | None = None,
    ) -> BackgroundTask:
        task = await self.task_service.create_task(task_type=task_type, payload=payload)
        await self.event_service.publish(
            event_type="TaskQueued",
            entity_type="background_task",
            entity_id=task.id,
            payload={"task_type": task.task_type},
        )
        await self.task_service.commit()
        await self.event_service.commit()
        return task

    async def list_tasks(
        self,
        *,
        task_type: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[BackgroundTask], int]:
        skip = (page - 1) * page_size
        items = await self.task_service.list_tasks(
            task_type=task_type,
            status=status,
            skip=skip,
            limit=page_size,
        )
        total = await self.task_service.count_tasks(
            task_type=task_type,
            status=status,
        )
        return items, total

    async def get_task(self, task_id: UUID) -> BackgroundTask | None:
        return await self.task_service.get_task(task_id)

    async def retry_task(self, task_id: UUID) -> BackgroundTask | None:
        task = await self.task_service.get_task(task_id)
        if task is None:
            return None
        if task.status != "failed":
            return task
        task = await self.task_service.retry_task(task_id)
        await self.event_service.publish(
            event_type="TaskQueued",
            entity_type="background_task",
            entity_id=task.id,
            payload={"task_type": task.task_type},
        )
        await self.task_service.commit()
        await self.event_service.commit()
        # 2026-08-25 P4 修复：commit 后 onupdate 列（updated_at）expired，
        # 路由 _serialize_task 同步访问触发 MissingGreenlet；refresh 加载。
        await self.task_service.refresh(task)
        return task


class DocumentApplicationService:
    def __init__(
        self,
        document_service: DocumentService,
        task_service: TaskService,
        event_service: EventService,
        storage: MinIOStorage,
        question_service: QuestionService | None = None,
    ) -> None:
        self.document_service = document_service
        self.task_service = task_service
        self.event_service = event_service
        self.storage = storage
        self.question_service = question_service

    async def upload_document(
        self,
        *,
        filename: str,
        file_type: str,
        file_obj: BinaryIO,
        size: int,
        content_type: str,
        subject: str | None = None,
        grade: str | None = None,
        year: int | None = None,
        school: str | None = None,
        ocr_model: str | None = None,
    ) -> tuple[Document, BackgroundTask]:
        object_key = f"documents/{uuid4().hex}/{Path(filename).name}"
        self.storage.put_object(
            object_key=object_key,
            file_obj=file_obj,
            size=size,
            content_type=content_type,
        )
        document = await self.document_service.register_document(
            filename=filename,
            file_type=file_type,
            object_key=object_key,
            subject=subject,
            grade=grade,
            year=year,
            school=school,
        )
        task = await self.task_service.create_task(
            task_type="document_parse",
            payload={"document_id": str(document.id), "ocr_model": ocr_model},
        )
        await self.event_service.publish(
            event_type="DocumentUploaded",
            entity_type="document",
            entity_id=document.id,
            payload={"document_id": str(document.id), "task_id": str(task.id)},
        )
        await self.document_service.commit()
        await self.task_service.commit()
        await self.event_service.commit()
        return document, task

    async def list_documents(
        self,
        *,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Document], int]:
        skip = (page - 1) * page_size
        items = await self.document_service.list_documents(
            status=status,
            skip=skip,
            limit=page_size,
        )
        total = await self.document_service.count_documents(status=status)
        return items, total

    async def get_document(self, document_id: UUID) -> Document | None:
        return await self.document_service.get_document(document_id)

    async def get_document_status(
        self,
        document_id: UUID,
    ) -> tuple[Document, BackgroundTask | None] | None:
        document = await self.document_service.get_document(document_id)
        if document is None:
            return None
        task = await self.task_service.latest_for_document(document_id)
        return document, task

    async def retry_document(self, document_id: UUID) -> BackgroundTask | None:
        document = await self.document_service.get_document(document_id)
        if document is None:
            return None
        self.document_service.reset_for_retry(document)
        task = await self.task_service.create_task(
            task_type="document_parse",
            payload={"document_id": str(document.id)},
        )
        await self.event_service.publish(
            event_type="DocumentRetryQueued",
            entity_type="document",
            entity_id=document.id,
            payload={"document_id": str(document.id), "task_id": str(task.id)},
        )
        await self.document_service.add_log(
            document.id,
            stage="retry",
            message="Document parse retry queued",
        )
        await self.document_service.commit()
        await self.task_service.commit()
        await self.event_service.commit()
        return task

    async def get_document_logs(
        self,
        document_id: UUID,
    ) -> list[Any] | None:
        document = await self.document_service.get_document(document_id)
        if document is None:
            return None
        return await self.document_service.get_logs(document_id)

    async def update_document_review(
        self,
        document_id: UUID,
        *,
        question_number: str,
        status: str,
        comment: str | None = None,
        overrides: dict[str, Any] | None = None,
        question_id: UUID | None = None,
    ) -> tuple[BackgroundTask | None, str | None]:
        result = await self.get_document_status(document_id)
        if result is None:
            return None, "NOT_FOUND"
        _, task = result
        if task is None or task.status != "succeeded" or not task.result_json:
            return None, "REVIEW_NOT_READY"

        # Phase 2A Step 2：先定位题目（只读），失败返回错误且不污染 task.result_json
        located: Question | None = None
        if self.question_service is not None:
            located = await self._locate_question_for_review(
                document_id,
                question_number,
                question_id=question_id,
                task_result_json=task.result_json,
            )
            if located is None:
                return None, "QUESTION_NOT_FOUND"

        result_json = dict(task.result_json)
        decisions = dict(result_json.get("review_decisions") or {})
        decision: dict[str, Any] = {
            "status": status,
            "comment": comment or "",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if question_id is not None:
            decision["question_id"] = str(question_id)
        decisions[question_number] = decision
        result_json["review_decisions"] = decisions
        if overrides is not None:
            overrides_by_question = dict(result_json.get("review_overrides") or {})
            overrides_by_question[question_number] = overrides
            result_json["review_overrides"] = overrides_by_question
        task.result_json = result_json

        # 审核决定写回 questions 表（不再只写 task.result_json）
        if self.question_service is not None and located is not None:
            await self.question_service.apply_review(
                located.id,
                status=status,
                overrides=overrides,
            )

        await self.task_service.commit()
        return task, None

    async def _locate_question_for_review(
        self,
        document_id: UUID,
        question_number: str,
        *,
        question_id: UUID | None,
        task_result_json: dict[str, Any],
    ) -> Question | None:
        """定位待审核题目（PLAN §7.1 Step 2）。

        优先级：
        1. 显式传入的 question_id（API body 或已有 review_decisions 中携带）；
        2. question_instances(document_id, source_question_number) 唯一定位，
           禁止按题号全局匹配任意同号题。
        """
        assert self.question_service is not None
        if question_id is None:
            existing_decision = (task_result_json.get("review_decisions") or {}).get(question_number) or {}
            existing_qid = existing_decision.get("question_id")
            if existing_qid:
                try:
                    question_id = UUID(str(existing_qid))
                except (ValueError, TypeError):
                    question_id = None
        if question_id is not None:
            return await self.question_service.get_question(question_id)
        return await self.question_service.find_by_document_and_question_number(
            document_id,
            question_number,
        )


class QuestionApplicationService:
    def __init__(
        self,
        question_service: QuestionService,
        event_service: EventService,
    ) -> None:
        self.question_service = question_service
        self.event_service = event_service

    async def create_question(
        self,
        *,
        subject_id: UUID,
        stem: str,
        options: list[dict[str, Any]] | None = None,
        answer: str | None = None,
        explanation: str | None = None,
        grade: str | None = None,
        question_type_id: UUID | None = None,
        score: Decimal | None = None,
        difficulty: int | None = None,
        source_type: str = "document",
        source_document_name: str | None = None,
        confidence: Decimal | None = None,
    ) -> Question:
        question = await self.question_service.create_question(
            subject_id=subject_id,
            stem=stem,
            options=options,
            answer=answer,
            explanation=explanation,
            grade=grade,
            question_type_id=question_type_id,
            score=score,
            difficulty=difficulty,
            source_type=source_type,
            source_document_name=source_document_name,
            confidence=confidence,
        )
        await self.event_service.publish(
            event_type="QuestionCreated",
            entity_type="question",
            entity_id=question.id,
            payload={"question_id": str(question.id)},
        )
        await self.question_service.commit()
        await self.event_service.commit()
        return question

    async def search_questions(
        self,
        *,
        subject_id: UUID | None = None,
        grade: str | None = None,
        year: int | None = None,
        school: str | None = None,
        question_type_id: UUID | None = None,
        knowledge_point: str | None = None,
        difficulty: int | None = None,
        source_type: str | None = None,
        status: str | None = None,
        confidence: float | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Question], int]:
        """Phase 2B 条件搜索：按学科/题型/知识点/年份/学校等筛选题目。"""
        skip = (page - 1) * page_size
        return await self.question_service.search(
            subject_id=subject_id,
            grade=grade,
            year=year,
            school=school,
            question_type_id=question_type_id,
            knowledge_point=knowledge_point,
            difficulty=difficulty,
            source_type=source_type,
            status=status,
            confidence=confidence,
            skip=skip,
            limit=page_size,
        )

    async def get_statistics(
        self,
        *,
        subject_id: UUID | None = None,
        grade: str | None = None,
        year: int | None = None,
        school: str | None = None,
        question_type_id: UUID | None = None,
        knowledge_point: str | None = None,
        difficulty: int | None = None,
        source_type: str | None = None,
        status: str | None = None,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> dict:
        """Phase 2B 统计聚合：total / question_type_distribution /
        knowledge_point_distribution / difficulty_distribution / year_trend / kp_year_trend。"""
        return await self.question_service.statistics(
            subject_id=subject_id,
            grade=grade,
            year=year,
            school=school,
            question_type_id=question_type_id,
            knowledge_point=knowledge_point,
            difficulty=difficulty,
            source_type=source_type,
            status=status,
            start_year=start_year,
            end_year=end_year,
        )

    async def get_question_detail(
        self, question_id: UUID
    ) -> tuple[Question | None, list, int]:
        """Phase 2B：题目详情（Question + 配图 + 出现次数派生值，ACS §5.3）。"""
        return await self.question_service.get_question_detail(question_id)

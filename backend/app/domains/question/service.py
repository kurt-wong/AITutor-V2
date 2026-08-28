import logging
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.domains.document.content_hash import compact_answer, compute_content_hash
from app.domains.question.repository import QuestionRepository
from app.models import Question, QuestionImage, QuestionType

logger = logging.getLogger(__name__)


class QuestionService:
    def __init__(self, repository: QuestionRepository) -> None:
        self.repository = repository

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
        question = Question(
            subject_id=subject_id,
            grade=grade,
            question_type_id=question_type_id,
            score=score,
            difficulty=difficulty,
            stem=stem,
            options=options,
            answer=answer,
            explanation=explanation,
            source_type=source_type,
            source_document_name=source_document_name,
            status="reviewing",
            confidence=confidence,
        )
        return await self.repository.add(question)

    async def review_question(
        self,
        question_id: UUID,
        *,
        status: str,
    ) -> Question | None:
        question = await self.repository.get(question_id)
        if question is None:
            return None
        question.status = status
        await self.repository.session.flush()
        return question

    async def get_question(self, question_id: UUID) -> Question | None:
        return await self.repository.get(question_id)

    async def get_question_detail(
        self, question_id: UUID
    ) -> tuple[Question | None, list[QuestionImage], int]:
        """题目详情：Question + 配图列表 + 出现次数（COUNT(instances) 派生）。

        Phase 2B（ACS §5.3）：详情返回题目内容、配图、答案、详解、元数据和出现次数。
        配图查询和 occurrence_count 派生在 Repository 层实现，可被真实 DB 集成测试覆盖。
        """
        question = await self.repository.get(question_id)
        if question is None:
            return None, [], 0
        images = await self.repository.list_images(question_id)
        occurrence_count = await self.repository.count_instances(question_id)
        return question, images, occurrence_count

    async def find_by_document_and_question_number(
        self,
        document_id: UUID,
        question_number: str,
    ) -> Question | None:
        """通过 question_instances(document_id, source_question_number) 唯一定位题目。"""
        return await self.repository.find_by_document_and_question_number(
            document_id,
            question_number,
        )

    async def apply_review(
        self,
        question_id: UUID,
        *,
        status: str,
        overrides: dict[str, Any] | None = None,
    ) -> Question | None:
        """Phase 2A Step 2：将审核决定写回 questions 表。

        - status: approved / rejected
        - overrides: 可选字段修正（stem/options/answer/explanation），
          只写回 overrides 中显式提供的键；options 为空列表时保留原值。
        - 内容字段修正（stem/options）走统一入口 update_question_content：
          重算 content_hash + exact duplicate 冲突检查（P0 生命周期修复，
          2026-08-27：此前改题干不重算 hash，旧 hash 残留、新内容无法去重）。
        """
        question = await self.repository.get(question_id)
        if question is None:
            return None
        question.status = status
        if overrides:
            await self._apply_content_update(question, overrides)
        await self.repository.session.flush()
        return question

    async def update_question_content(
        self,
        question_id: UUID,
        *,
        stem: str | None = None,
        options: list[dict[str, Any]] | None = None,
        answer: str | None = None,
        explanation: str | None = None,
        sub_questions: list[dict[str, Any]] | None = None,
        question_type: str | None = None,
    ) -> Question | None:
        """统一领域入口：更新题目内容并维护 content_hash 生命周期。

        - 参数为 None 表示该字段不变；显式传值才更新。
        - 影响 hash 的字段（stem/options/sub_questions/question_type）变化时：
          重算 content_hash → 查 exact duplicate（同学科同 hash 排除自身）→
          答案不同则标记 answer_conflict 审核，不静默覆盖。
        - question_type 为 canonical code（如 "single_choice"）；缺省时从
          question_type_id 反查 QuestionType.code。

        2026-08-27（P0 content_hash 生命周期）：apply_review 与外部调用
        统一走本入口，保证内容与 hash 不漂移（旧 hash 不残留）。
        """
        question = await self.repository.get(question_id)
        if question is None:
            return None
        updates: dict[str, Any] = {}
        if stem is not None:
            updates["stem"] = stem
        if options is not None:
            updates["options"] = options
        if answer is not None:
            updates["answer"] = answer
        if explanation is not None:
            updates["explanation"] = explanation
        if sub_questions is not None:
            updates["sub_questions"] = sub_questions
        if question_type is not None:
            updates["question_type"] = question_type
        await self._apply_content_update(question, updates)
        await self.repository.session.flush()
        return question

    async def _apply_content_update(
        self,
        question: Question,
        updates: dict[str, Any],
    ) -> None:
        """统一内容更新实现：应用字段 → 检测 hash 相关变化 → 重算 hash → 冲突检查。

        被 apply_review（overrides）与 update_question_content 共用，
        保证「内容变化 → 重算 content_hash → 查 exact duplicate → 冲突标记审核」
        的生命周期约束在所有写路径上一致。
        """
        hash_fields_changed = False

        if updates.get("stem") is not None and updates["stem"] != question.stem:
            question.stem = updates["stem"]
            hash_fields_changed = True
        if "options" in updates and updates.get("options"):
            if updates["options"] != question.options:
                question.options = updates["options"]
                hash_fields_changed = True
        if (
            updates.get("sub_questions") is not None
            and updates["sub_questions"] != question.sub_questions
        ):
            question.sub_questions = updates["sub_questions"]
            hash_fields_changed = True
        if updates.get("answer") is not None:
            question.answer = updates["answer"]
        if updates.get("explanation") is not None:
            question.explanation = updates["explanation"]

        # 非内容字段（仅 status 等）或内容未变化 → 不需要重算 hash
        if not hash_fields_changed:
            return

        # 重算 content_hash：question_type 显式传入优先，否则从 question_type_id 反查
        qtype = updates.get("question_type")
        if qtype is None:
            qtype = await self._resolve_question_type_code(question.question_type_id)
        new_hash = compute_content_hash(
            stem=question.stem,
            options=question.options,
            question_type=qtype,
            sub_questions=question.sub_questions,
        )

        # 查 exact duplicate（同学科、同 hash、排除自身）
        dup = await self.repository.find_by_content_hash_excluding(
            new_hash, question.subject_id, question.id
        )
        if dup is not None:
            existing_answer = (dup.answer or "").strip()
            new_answer = (question.answer or "").strip()
            if (
                new_answer
                and existing_answer
                and compact_answer(new_answer) != compact_answer(existing_answer)
            ):
                # hash 相同但答案不同 → 冲突进审核（不静默覆盖，与 ingestion 一致）
                question.review_reason = (
                    f"answer_conflict:{question.source_document_name or 'review'}:{new_answer}"
                )[:200]
                if question.status == "approved":
                    question.status = "reviewing"
                logger.warning(
                    "content update: question %s hash=%s collides with %s (answer conflict) → reviewing",
                    question.id, new_hash[:12], dup.id,
                )
            else:
                # hash 相同且答案归一化一致 → 同一题，不标记冲突
                logger.info(
                    "content update: question %s hash=%s collides with %s (answers equal)",
                    question.id, new_hash[:12], dup.id,
                )

        question.content_hash = new_hash  # 旧 hash 不残留

    async def _resolve_question_type_code(
        self,
        question_type_id: UUID | None,
    ) -> str | None:
        """从 question_type_id 反查 canonical code（重算 hash 需要题型字符串）。"""
        if question_type_id is None:
            return None
        stmt = select(QuestionType.code).where(QuestionType.id == question_type_id)
        return await self.repository.session.scalar(stmt)

    async def search(
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
        source_document_name: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Question], int]:
        """Phase 2B 条件搜索。"""
        return await self.repository.search(
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
            source_document_name=source_document_name,
            skip=skip,
            limit=limit,
        )

    async def catalog(self) -> list[dict]:
        """题库目录聚合：学科 → 年级 → 题目数。"""
        return await self.repository.catalog()

    async def statistics(
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
        """Phase 2B 统计聚合。"""
        return await self.repository.statistics(
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

    async def commit(self) -> None:
        await self.repository.commit()

from decimal import Decimal
from typing import Any
from uuid import UUID

from app.domains.question.repository import QuestionRepository
from app.models import Question, QuestionImage


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
        """
        question = await self.repository.get(question_id)
        if question is None:
            return None
        question.status = status
        if overrides:
            if overrides.get("stem") is not None:
                question.stem = overrides["stem"]
            if overrides.get("answer") is not None:
                question.answer = overrides["answer"]
            if overrides.get("explanation") is not None:
                question.explanation = overrides["explanation"]
            if "options" in overrides and overrides.get("options"):
                question.options = overrides["options"]
        await self.repository.session.flush()
        return question

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
            skip=skip,
            limit=limit,
        )

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

from decimal import Decimal
from typing import Any
from uuid import UUID

from app.domains.question.repository import QuestionRepository
from app.models import Question


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
        year: int | None = None,
        school: str | None = None,
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
            year=year,
            school=school,
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

    async def commit(self) -> None:
        await self.repository.commit()

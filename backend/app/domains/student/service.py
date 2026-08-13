from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.domains.student.repository import (
    MasteryRecordRepository,
    PracticeAnswerRepository,
    PracticeSessionRepository,
)
from app.models import PracticeAnswer, PracticeSession


class PracticeService:
    def __init__(
        self,
        session_repository: PracticeSessionRepository,
        answer_repository: PracticeAnswerRepository,
        mastery_repository: MasteryRecordRepository,
    ) -> None:
        self.session_repository = session_repository
        self.answer_repository = answer_repository
        self.mastery_repository = mastery_repository

    async def create_session(
        self,
        *,
        user_id: UUID,
        trigger_type: str,
        question_count: int | None = None,
    ) -> PracticeSession:
        session = PracticeSession(
            user_id=user_id,
            trigger_type=trigger_type,
            question_count=question_count,
            status="in_progress",
            started_at=datetime.now(timezone.utc),
        )
        return await self.session_repository.add(session)

    async def record_answer(
        self,
        *,
        session_id: UUID,
        question_id: UUID,
        student_answer: str | None,
        is_correct: bool | None,
        duration_seconds: int | None = None,
        question_snapshot: dict[str, Any] | None = None,
        knowledge_point_ids: list[UUID] | None = None,
    ) -> PracticeAnswer:
        answer = PracticeAnswer(
            session_id=session_id,
            question_id=question_id,
            question_snapshot=question_snapshot,
            student_answer=student_answer,
            is_correct=is_correct,
            duration_seconds=duration_seconds,
            knowledge_point_ids=knowledge_point_ids,
        )
        return await self.answer_repository.add(answer)

    async def commit(self) -> None:
        await self.session_repository.commit()

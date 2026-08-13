from datetime import datetime, timezone
from uuid import UUID

from app.domains.wrong_question.repository import WrongQuestionRepository
from app.models import WrongQuestion


class WrongQuestionService:
    def __init__(self, repository: WrongQuestionRepository) -> None:
        self.repository = repository

    async def record_wrong(
        self,
        *,
        user_id: UUID,
        question_id: UUID,
        source_type: str,
        error_type: str | None = None,
    ) -> WrongQuestion:
        wrong_question = WrongQuestion(
            user_id=user_id,
            question_id=question_id,
            source_type=source_type,
            error_type=error_type,
            last_wrong_time=datetime.now(timezone.utc),
            mastery_status="not_mastered",
        )
        return await self.repository.add(wrong_question)

    async def update_mastery(
        self,
        wrong_question_id: UUID,
        *,
        mastery_status: str,
    ) -> WrongQuestion | None:
        wrong_question = await self.repository.get(wrong_question_id)
        if wrong_question is None:
            return None
        wrong_question.mastery_status = mastery_status
        wrong_question.last_review_at = datetime.now(timezone.utc)
        wrong_question.review_count += 1
        await self.repository.session.flush()
        return wrong_question

    async def commit(self) -> None:
        await self.repository.commit()

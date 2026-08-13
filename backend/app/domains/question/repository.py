from sqlalchemy import select

from app.models import (
    Question,
    QuestionEmbedding,
    QuestionImage,
    QuestionInstance,
    QuestionKnowledge,
)
from app.repositories.base import BaseRepository


class QuestionRepository(BaseRepository[Question]):
    model = Question

    async def list_by_filters(
        self,
        *,
        status: str | None = None,
        source_type: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Question]:
        stmt = select(Question)
        if status is not None:
            stmt = stmt.where(Question.status == status)
        if source_type is not None:
            stmt = stmt.where(Question.source_type == source_type)
        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.scalars(stmt)
        return list(result)


class QuestionInstanceRepository(BaseRepository[QuestionInstance]):
    model = QuestionInstance


class QuestionImageRepository(BaseRepository[QuestionImage]):
    model = QuestionImage


class QuestionKnowledgeRepository(BaseRepository[QuestionKnowledge]):
    model = QuestionKnowledge


class QuestionEmbeddingRepository(BaseRepository[QuestionEmbedding]):
    model = QuestionEmbedding

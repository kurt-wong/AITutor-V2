from uuid import UUID

from sqlalchemy import select

from app.models import KnowledgeNode, QuestionType
from app.repositories.base import BaseRepository


class KnowledgeNodeRepository(BaseRepository[KnowledgeNode]):
    model = KnowledgeNode

    async def find_by_code(self, code: str) -> KnowledgeNode | None:
        """按唯一 code 查找知识树节点。"""
        stmt = select(KnowledgeNode).where(KnowledgeNode.code == code).limit(1)
        return await self.session.scalar(stmt)


class QuestionTypeRepository(BaseRepository[QuestionType]):
    model = QuestionType

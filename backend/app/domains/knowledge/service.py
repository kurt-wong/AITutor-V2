from uuid import UUID

from app.domains.knowledge.repository import (
    KnowledgeNodeRepository,
    QuestionTypeRepository,
)
from app.models import KnowledgeNode, QuestionType


class KnowledgeService:
    def __init__(
        self,
        node_repository: KnowledgeNodeRepository,
        question_type_repository: QuestionTypeRepository,
    ) -> None:
        self.node_repository = node_repository
        self.question_type_repository = question_type_repository

    async def create_node(
        self,
        *,
        subject_id: UUID,
        code: str,
        name: str,
        parent_id: UUID | None = None,
        level: int = 0,
        description: str | None = None,
    ) -> KnowledgeNode:
        node = KnowledgeNode(
            subject_id=subject_id,
            parent_id=parent_id,
            code=code,
            name=name,
            level=level,
            description=description,
        )
        return await self.node_repository.add(node)

    async def create_question_type(
        self,
        *,
        subject_id: UUID,
        code: str,
        name: str,
        parent_id: UUID | None = None,
        sort_order: int = 0,
    ) -> QuestionType:
        question_type = QuestionType(
            subject_id=subject_id,
            parent_id=parent_id,
            code=code,
            name=name,
            sort_order=sort_order,
        )
        return await self.question_type_repository.add(question_type)

    async def commit(self) -> None:
        await self.node_repository.commit()

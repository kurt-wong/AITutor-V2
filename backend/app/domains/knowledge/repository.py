from app.models import KnowledgeNode, QuestionType
from app.repositories.base import BaseRepository


class KnowledgeNodeRepository(BaseRepository[KnowledgeNode]):
    model = KnowledgeNode


class QuestionTypeRepository(BaseRepository[QuestionType]):
    model = QuestionType

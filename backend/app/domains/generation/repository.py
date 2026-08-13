from app.models import GenerationJob, GenerationResult
from app.repositories.base import BaseRepository


class GenerationJobRepository(BaseRepository[GenerationJob]):
    model = GenerationJob


class GenerationResultRepository(BaseRepository[GenerationResult]):
    model = GenerationResult

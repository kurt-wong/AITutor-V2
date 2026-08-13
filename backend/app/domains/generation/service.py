from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.domains.generation.repository import (
    GenerationJobRepository,
    GenerationResultRepository,
)
from app.models import GenerationJob, GenerationResult


class GenerationService:
    def __init__(
        self,
        job_repository: GenerationJobRepository,
        result_repository: GenerationResultRepository,
    ) -> None:
        self.job_repository = job_repository
        self.result_repository = result_repository

    async def create_job(
        self,
        *,
        task_id: UUID,
        task_type: str,
        subject: str | None = None,
        grade: str | None = None,
        parameters: dict[str, Any] | None = None,
        ratio_snapshot: dict[str, Any] | None = None,
    ) -> GenerationJob:
        job = GenerationJob(
            task_id=task_id,
            task_type=task_type,
            subject=subject,
            grade=grade,
            parameters=parameters,
            ratio_snapshot=ratio_snapshot,
        )
        return await self.job_repository.add(job)

    async def create_result(
        self,
        *,
        job_id: UUID,
        question_id: UUID,
    ) -> GenerationResult:
        result = GenerationResult(
            job_id=job_id,
            question_id=question_id,
            review_status="pending",
        )
        return await self.result_repository.add(result)

    async def complete_job(self, job_id: UUID) -> None:
        job = await self.job_repository.get(job_id)
        if job is not None:
            job.completed_at = datetime.now(timezone.utc)
        await self.job_repository.session.flush()

    async def commit(self) -> None:
        await self.job_repository.commit()

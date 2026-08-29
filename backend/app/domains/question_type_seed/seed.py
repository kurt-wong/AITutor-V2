"""
Seed question types from Python seed definitions -> DB.

Reads all 9-subject question type trees from data/ Python files
and inserts/upserts them into the question_types table.

Two-phase approach:
  Phase 1: Create all QuestionType records (level 1, 2, 3) without parent_id
  Phase 2: Set parent_id by matching parent_code -> id

Idempotent: re-running won't duplicate records (matched by code).

Usage:
    cd backend
    .venv/Scripts/python.exe -m app.domains.question_type_seed.seed
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tables import QuestionType, Subject
from app.domains.question_type_seed.data import ALL_QUESTION_TYPE_SEEDS
from app.domains.question_type_seed.types import QuestionTypeSeed


async def seed_question_types(session: AsyncSession) -> int:
    """Seed all question types into the database.

    Returns count of created + updated records.
    """
    created = 0
    updated = 0

    # -- Build subject map: code -> UUID
    result = await session.execute(select(Subject))
    subject_map: dict[str, UUID] = {s.code: s.id for s in result.scalars().all()}

    # -- Load all existing question types by code
    result = await session.execute(select(QuestionType))
    existing_by_code: dict[str, QuestionType] = {
        qt.code: qt for qt in result.scalars().all()
    }

    # -- Phase 1: Create or update all question type records
    #    Process level 1 first, then 2, then 3 so parents exist before children.
    all_seeds: list[QuestionTypeSeed] = []
    for seeds in ALL_QUESTION_TYPE_SEEDS.values():
        all_seeds.extend(seeds)

    # Sort by level so parents are created first
    sorted_seeds = sorted(all_seeds, key=lambda s: s.level)

    # Map seed code -> DB id for parent resolution
    code_to_id: dict[str, UUID] = {qt.code: qt.id for qt in existing_by_code.values()}

    for seed in sorted_seeds:
        # Determine subject code from seed code prefix
        subj_code = seed.code.split("-")[0]
        subject_id = subject_map.get(subj_code)
        if subject_id is None:
            print(f"  WARN: Unknown subject '{subj_code}' for seed {seed.code}")
            continue

        existing = existing_by_code.get(seed.code)
        if existing:
            changed = False
            if existing.name != seed.name:
                existing.name = seed.name
                changed = True
            if existing.level != seed.level:
                existing.level = seed.level
                changed = True
            if existing.description != seed.description:
                existing.description = seed.description
                changed = True
            if existing.keywords != seed.keywords:
                existing.keywords = seed.keywords
                changed = True
            if changed:
                updated += 1
            code_to_id[seed.code] = existing.id
        else:
            qt = QuestionType(
                subject_id=subject_id,
                parent_id=None,  # resolved in Phase 2
                code=seed.code,
                name=seed.name,
                sort_order=seed.level,
                level=seed.level,
                description=seed.description,
                keywords=seed.keywords,
            )
            session.add(qt)
            await session.flush()  # get the UUID
            code_to_id[qt.code] = qt.id
            created += 1

    await session.commit()

    # -- Phase 2: Resolve parent_id references
    parent_updates = 0
    for seed in sorted_seeds:
        if not seed.parent_code:
            continue
        child_id = code_to_id.get(seed.code)
        parent_id = code_to_id.get(seed.parent_code)
        if child_id and parent_id:
            await session.execute(
                QuestionType.__table__.update()
                .where(QuestionType.id == child_id)
                .where(QuestionType.parent_id.is_(None))
                .values(parent_id=parent_id)
            )
            parent_updates += 1

    await session.commit()

    total = created + updated
    print(f"  Question types: {created} created, {updated} updated, "
          f"{parent_updates} parent links resolved")
    return total


# ═══ CLI Entry Point ═════════════════════════════════════════════════════════

async def main():
    from app.core.database import async_session_factory

    print("=" * 60)
    print("Question Type Seed")
    print("=" * 60)

    # Count seeds
    total_seeds = sum(len(v) for v in ALL_QUESTION_TYPE_SEEDS.values())
    total_subjects = len(ALL_QUESTION_TYPE_SEEDS)
    print(f"  Python definitions: {total_seeds} question types across "
          f"{total_subjects} subjects")

    async with async_session_factory() as session:
        total = await seed_question_types(session)

    print("-" * 60)
    print(f"  Total processed: {total}")
    print("=" * 60)
    print("Seed complete.")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

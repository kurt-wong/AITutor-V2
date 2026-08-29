"""Question type tree API endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models.tables import QuestionType, Subject

router = APIRouter(prefix="/api/admin/question-types", tags=["question-types"])

# Subject code -> Chinese name mapping
_SUBJECT_NAMES = {
    "MATH": "数学", "PHYS": "物理", "CHEM": "化学", "BIO": "生物",
    "CHN": "语文", "ENG": "英语", "POLI": "政治", "HIST": "历史", "GEOG": "地理",
}


@router.get("")
async def get_question_type_tree(
    subject: str | None = Query(None, description="Filter by subject code (MATH/ENG/...)"),
    db: AsyncSession = Depends(get_db_session),
):
    """Return the full question type hierarchy as a tree.

    Optional ?subject=ENG filters to one subject.
    """
    # Load all question types
    stmt = select(QuestionType).order_by(QuestionType.sort_order)
    if subject:
        # Find subject ID first
        subj_stmt = select(Subject).where(Subject.code == subject)
        subj = await db.scalar(subj_stmt)
        if subj:
            stmt = stmt.where(QuestionType.subject_id == subj.id)
    types = list(await db.scalars(stmt))

    # Group by subject
    subject_map: dict[str, list] = {}
    for qt in types:
        subj_code = qt.code.split("-")[0]
        subject_map.setdefault(subj_code, []).append(qt)

    # Build tree: L1 -> L2 -> L3
    def build_node(qt: QuestionType) -> dict:
        children = [
            build_node(child)
            for child in types
            if child.parent_id == qt.id
        ]
        return {
            "code": qt.code,
            "name": qt.name,
            "level": qt.level,
            "description": qt.description,
            "keywords": qt.keywords,
            "children": children if children else None,
        }

    result = []
    for subj_code, subj_types in sorted(subject_map.items()):
        # Find L1 nodes for this subject
        l1_nodes = [qt for qt in subj_types if qt.level == 1]
        if not l1_nodes:
            continue
        result.append({
            "code": subj_code,
            "name": _SUBJECT_NAMES.get(subj_code, subj_code),
            "types": [build_node(n) for n in sorted(l1_nodes, key=lambda x: x.sort_order)],
        })

    return {"subjects": result}

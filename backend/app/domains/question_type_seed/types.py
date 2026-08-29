"""
Question Type Seed -- core data types.

Encoding: {SUBJ}-{CATEGORY}-{SUBCATEGORY}
  Level 1 (SUBJ):       subject root        e.g. ENG
  Level 2 (CATEGORY):   major question type  e.g. ENG-READ
  Level 3 (SUBCATEGORY):specific type        e.g. ENG-READ-DETAIL

Subject codes:
  MATH, PHYS, CHEM, BIO, CHN, ENG, POLI, HIST, GEOG
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class QuestionTypeSeed:
    """Question type definition (seed data before DB insertion)."""

    code: str           # e.g. "ENG-READ-DETAIL"
    name: str           # e.g. "细节理解"
    level: int          # 1=大题型, 2=子类, 3=细粒度
    parent_code: str | None  # None for level-1 nodes
    description: str = ""
    keywords: list[str] = field(default_factory=list)

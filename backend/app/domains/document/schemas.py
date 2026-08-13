from typing import Any

from pydantic import BaseModel, Field


class ParsedImage(BaseModel):
    id: str
    url: str | None = None
    local_path: str | None = None
    page_number: int | None = None
    role: str = "diagram"
    caption: str | None = None
    bbox: dict | None = None  # {"x1": 0, "y1": 0, "x2": 100, "y2": 20}


class OcrBlock(BaseModel):
    """PP-StructureV3 单个 block（从 prunedResult.parsing_res_list 解析）。"""
    label: str  # text / formula / table / doc_title / ...
    content: str
    bbox: dict | None = None  # {"x1": 0, "y1": 0, "x2": 100, "y2": 20}


class OcrPage(BaseModel):
    page_number: int
    markdown: str
    images: list[ParsedImage] = Field(default_factory=list)
    blocks: list[OcrBlock] = Field(default_factory=list)  # PP block-level data with bbox
    source_provider: str = "paddleocr"


class OcrDocument(BaseModel):
    filename: str
    pages: list[OcrPage] = Field(default_factory=list)
    provider_used: str | None = None


class ParsedQuestion(BaseModel):
    question_number: str | None = None
    stem: str = ""
    options: list[Any] = Field(default_factory=list)
    answer: str | None = None
    explanation: str | None = None
    images: list[str] = Field(default_factory=list)
    question_type: str | None = None
    difficulty: int | None = None
    score: float | None = None
    knowledge_points: list[str] = Field(default_factory=list)
    confidence: float = 0.5
    issues: list[str] = Field(default_factory=list)
    source_page: int | None = None


class QuestionAggregate(BaseModel):
    filename: str
    subject: str | None = None
    grade: str | None = None
    year: int | None = None
    school: str | None = None
    questions: list[ParsedQuestion] = Field(default_factory=list)
    confidence: float = 0.5
    provider: str | None = None
    warnings: list[str] = Field(default_factory=list)

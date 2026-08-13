"""
DEPRECATED — 临时验证版，禁止用于正式链路。

本文件是 P2 阶段的临时验证实现，让 LLM 直接输出题干/选项/答案/解析文本。
这违反 V1_LESSONS 3.1/3.16（LLM 不得直接输出题目原文）。

正式链路必须使用：
- line_annotator.py（LLM 行号标注）
- anchor_corrector.py（锚点校正）
- content_slicer.py（内容切片）
- answer_matcher.py（答案独立匹配）

详见 Docs/01_Product/T3_IMPLEMENTATION.md。
"""

import os

# 运行时拦截：正式环境禁止导入此模块
if os.environ.get("APP_ENV") == "production":
    raise ImportError(
        "question_extractor.py 已废弃，禁止在正式环境使用。"
        "请使用 line_annotator.py + anchor_corrector.py + content_slicer.py + answer_matcher.py"
    )

import json
from typing import Any

from app.ai.json_utils import parse_json_object
from app.ai.gateway import LLMGateway, get_llm_gateway
from app.domains.document.schemas import ParsedQuestion, QuestionAggregate


class QuestionExtractionError(RuntimeError):
    pass


class LLMQuestionExtractor:
    def __init__(
        self,
        gateway: LLMGateway | None = None,
        *,
        max_input_chars: int = 60000,
    ) -> None:
        self.gateway = gateway or get_llm_gateway()
        self.max_input_chars = max_input_chars

    async def extract(
        self,
        *,
        filename: str,
        markdown: str,
        metadata: dict[str, Any] | None = None,
    ) -> QuestionAggregate:
        metadata = metadata or {}
        prompt = _build_prompt(
            filename=filename,
            markdown=markdown,
            metadata=metadata,
            max_input_chars=self.max_input_chars,
        )
        raw = await self.gateway.complete(prompt, temperature=0.0)
        try:
            payload = _parse_json(raw)
        except Exception as exc:
            raise QuestionExtractionError("LLM question extraction returned invalid JSON") from exc

        aggregate = _aggregate_from_payload(
            filename=filename,
            metadata=metadata,
            payload=payload,
        )
        if not aggregate.questions:
            raise QuestionExtractionError("LLM question extraction returned no questions")
        return aggregate


def _build_prompt(
    *,
    filename: str,
    markdown: str,
    metadata: dict[str, Any],
    max_input_chars: int,
) -> str:
    input_markdown = markdown
    if len(input_markdown) > max_input_chars:
        input_markdown = input_markdown[:max_input_chars]
    metadata_json = json.dumps(metadata, ensure_ascii=False)
    return f"""你是高中试卷结构化提取器。输入是 PP-StructureV3 导出的 Markdown，可能包含题目、选项、答案、解析、公式、表格和图片引用。
请把所有题目整理为 Question Aggregate JSON。不要输出 Markdown 代码块，不要输出额外解释，只输出合法 JSON。

文档文件名：{filename}
已知文档元数据：{metadata_json}

输出结构：
{{
  "subject": "学科",
  "grade": "年级",
  "year": 年份或 null,
  "school": "学校或 null",
  "confidence": 0.0,
  "warnings": [],
  "questions": [
    {{
      "question_number": "1",
      "stem": "题干",
      "options": [{{"label": "A", "text": "选项内容"}}],
      "answer": "标准答案",
      "explanation": "解析",
      "images": ["图片引用"],
      "question_type": "题型",
      "difficulty": 3,
      "score": 5,
      "knowledge_points": ["知识点"],
      "confidence": 0.0,
      "issues": ["缺失项说明"],
      "source_page": 1
    }}
  ]
}}

规则：
1. 文末答案必须按题号匹配回原题；题后答案就近匹配。
2. 题干、选项、答案、解析缺失时保留缺失字段为 null，并在 issues 中说明。
3. 图片只从文档中可见的图片引用中选取，输出图片 id 或引用文本。
4. 无法判断的元数据使用 null，不要编造。
5. confidence 使用 0 到 1 的小数，0.95 以上表示可直接入库，低于 0.8 应在 issues 中说明。

Markdown 内容：
{input_markdown}
"""


def _parse_json(raw: str) -> dict[str, Any]:
    return parse_json_object(raw)


def _aggregate_from_payload(
    *,
    filename: str,
    metadata: dict[str, Any],
    payload: dict[str, Any],
) -> QuestionAggregate:
    questions: list[ParsedQuestion] = []
    for raw_question in payload.get("questions") or []:
        if not isinstance(raw_question, dict):
            continue
        question = _question_from_payload(raw_question)
        if question:
            questions.append(question)

    if not questions:
        return QuestionAggregate(
            filename=filename,
            subject=_first_string(payload.get("subject"), metadata.get("subject")),
            grade=_first_string(payload.get("grade"), metadata.get("grade")),
            year=_int_or_none(payload.get("year"), metadata.get("year")),
            school=_first_string(payload.get("school"), metadata.get("school")),
            confidence=_float_or_default(payload.get("confidence"), 0.0),
            warnings=payload.get("warnings") or [],
        )

    confidence_values = [question.confidence for question in questions]
    return QuestionAggregate(
        filename=filename,
        subject=_first_string(payload.get("subject"), metadata.get("subject")),
        grade=_first_string(payload.get("grade"), metadata.get("grade")),
        year=_int_or_none(payload.get("year"), metadata.get("year")),
        school=_first_string(payload.get("school"), metadata.get("school")),
        questions=questions,
        confidence=_float_or_default(
            payload.get("confidence"),
            sum(confidence_values) / len(confidence_values),
        ),
        warnings=payload.get("warnings") or [],
    )


def _question_from_payload(raw: dict[str, Any]) -> ParsedQuestion | None:
    stem = str(raw.get("stem") or "").strip()
    issues = list(raw.get("issues") or [])
    if not stem:
        issues.append("missing_stem")
    return ParsedQuestion(
        question_number=_str_or_none(
            raw.get("question_number") or raw.get("qno") or raw.get("number")
        ),
        stem=stem,
        options=raw.get("options") or [],
        answer=_str_or_none(raw.get("answer")),
        explanation=_str_or_none(
            raw.get("explanation") or raw.get("solution")
        ),
        images=[str(item) for item in (raw.get("images") or [])],
        question_type=_str_or_none(raw.get("question_type") or raw.get("questionType")),
        difficulty=_int_or_none(raw.get("difficulty")),
        score=_float_or_none(raw.get("score")),
        knowledge_points=[str(item) for item in (raw.get("knowledge_points") or [])],
        confidence=_float_or_default(raw.get("confidence"), 0.5),
        issues=issues,
        source_page=_int_or_none(raw.get("source_page")),
    )


def _str_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _first_string(*values: Any) -> str | None:
    for value in values:
        text = _str_or_none(value)
        if text:
            return text
    return None


def _int_or_none(*values: Any) -> int | None:
    for value in values:
        if value is None or value == "":
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def _float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _float_or_default(value: Any, default: float) -> float:
    parsed = _float_or_none(value)
    if parsed is None:
        return default
    return max(0.0, min(1.0, parsed))

"""LLM 行号标注器单元测试。"""

import json

import pytest

from app.ai.gateway import LLMGateway
from app.ai.providers import MockLLMProvider
from app.domains.document.line_annotator import annotate_document, build_annotation_prompt
from app.domains.document.schemas_l1 import L1Document, L1Line, L1Page


def _make_simple_doc() -> L1Document:
    """构造简单的测试 L1 文档。"""
    lines = [
        L1Line("P1L001", 1, 1, 1, "一、选择题", "text"),
        L1Line("P1L002", 1, 2, 2, "1. 已知函数f(x)=2x+1，则f(3)=", "text"),
        L1Line("P1L003", 1, 3, 3, "（A）5", "text"),
        L1Line("P1L004", 1, 4, 4, "（B）6", "text"),
        L1Line("P1L005", 1, 5, 5, "（C）7", "text"),
        L1Line("P1L006", 1, 6, 6, "（D）8", "text"),
        L1Line("P1L007", 1, 7, 7, "2. 计算：√4 + √9 =", "text"),
        L1Line("P1L008", 1, 8, 8, "（A）3", "text"),
        L1Line("P1L009", 1, 9, 9, "（B）4", "text"),
        L1Line("P1L010", 1, 10, 10, "（C）5", "text"),
        L1Line("P1L011", 1, 11, 11, "（D）6", "text"),
    ]
    return L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source="native",
        total_pages=1,
    )


def _mock_llm_response() -> str:
    """构造 mock LLM 响应。"""
    return json.dumps({
        "filename": "test.pdf",
        "subject": "数学",
        "questions": [
            {
                "question_number": "1",
                "question_type": "single_choice",
                "section_id": "选择题",
                "stem_line_ids": ["P1L002"],
                "options_line_ids": {
                    "A": ["P1L003"],
                    "B": ["P1L004"],
                    "C": ["P1L005"],
                    "D": ["P1L006"],
                },
                "difficulty": 1,
                "score": 5.0,
                "knowledge_points": ["函数求值"],
            },
            {
                "question_number": "2",
                "question_type": "single_choice",
                "section_id": "选择题",
                "stem_line_ids": ["P1L007"],
                "options_line_ids": {
                    "A": ["P1L008"],
                    "B": ["P1L009"],
                    "C": ["P1L010"],
                    "D": ["P1L011"],
                },
                "difficulty": 1,
                "score": 5.0,
                "knowledge_points": ["根式运算"],
            },
        ],
        "metadata_confidence": 0.9,
        "warnings": [],
    })


def test_build_annotation_prompt_contains_line_ids():
    """Prompt 包含行号引用。"""
    doc = _make_simple_doc()
    prompt = build_annotation_prompt(doc)
    assert "P1L001" in prompt
    assert "P1L011" in prompt
    assert "1. 已知函数f(x)=2x+1" in prompt
    assert "single_choice / multiple_choice / fill_in / true_false / short_answer" in prompt


def test_annotate_returns_l2_annotation():
    """标注返回 L2DocumentAnnotation。"""
    doc = _make_simple_doc()
    gateway = LLMGateway(
        mode="live",
        providers=[MockLLMProvider(response=_mock_llm_response())],
    )

    import asyncio
    result = asyncio.run(annotate_document(doc, gateway))

    assert result.filename == "test.pdf"
    assert result.subject == "数学"
    assert len(result.questions) == 2
    assert result.questions[0].question_number == "1"
    assert result.questions[0].question_type == "single_choice"
    assert result.questions[0].stem_line_ids == ["P1L002"]
    assert result.questions[0].options_line_ids["A"] == ["P1L003"]


def test_annotate_filters_invalid_line_ids():
    """标注过滤无效行 ID。"""
    doc = _make_simple_doc()

    response = json.dumps({
        "filename": "test.pdf",
        "questions": [
            {
                "question_number": "1",
                "question_type": "single_choice",
                "stem_line_ids": ["P1L002", "P1L999"],
                "options_line_ids": {
                    "A": ["P1L003"],
                    "B": ["P1L998"],
                },
            }
        ],
        "metadata_confidence": 0.5,
    })

    gateway = LLMGateway(
        mode="live",
        providers=[MockLLMProvider(response=response)],
    )

    import asyncio
    result = asyncio.run(annotate_document(doc, gateway))

    assert result.questions[0].stem_line_ids == ["P1L002"]
    assert result.questions[0].options_line_ids["A"] == ["P1L003"]
    assert result.questions[0].options_line_ids["B"] == []


def test_annotate_handles_fenced_json():
    """标注处理 markdown fence 包裹的 JSON。"""
    doc = _make_simple_doc()
    fenced_response = f"```json\n{_mock_llm_response()}\n```"
    gateway = LLMGateway(
        mode="live",
        providers=[MockLLMProvider(response=fenced_response)],
    )

    import asyncio
    result = asyncio.run(annotate_document(doc, gateway))
    assert len(result.questions) == 2

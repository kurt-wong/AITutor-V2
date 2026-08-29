"""文档处理管线单元测试。"""

import json
import pytest
from pathlib import Path

from app.ai.gateway import LLMGateway
from app.ai.providers import MockLLMProvider
from app.domains.document.pipeline_shared import PipelineResult
from app.domains.document.pipeline import run_pipeline
from app.domains.document.schemas_l2 import L2SubQuestion, SlicedQuestion

TEST_PDF = (
    Path(__file__).resolve().parents[2]
    / "test"
    / "pdf"
    / "2026北京朝阳高一（上）期末数学（教师版）.pdf"
)


def _mock_llm_response() -> str:
    """构造 mock LLM 响应。"""
    return json.dumps({
        "filename": "test.pdf",
        "subject": "数学",
        "questions": [
            {
                "question_number": "2",
                "question_type": "single_choice",
                "section_id": "选择题",
                "stem_line_ids": ["P1L010"],
                "options_line_ids": {
                    "A": ["P1L011"],
                    "B": ["P1L012"],
                    "C": ["P1L013"],
                    "D": ["P1L014"],
                },
                "difficulty": 2,
                "score": 5.0,
                "knowledge_points": ["函数"],
            },
        ],
        "metadata_confidence": 0.8,
        "warnings": [],
    })


def test_pipeline_result_structure():
    """PipelineResult 结构正确。"""
    result = PipelineResult()
    assert result.stages == []
    assert result.sliced_questions == []
    assert result.errors == []
    assert result.to_dict()["question_count"] == 0


def test_pipeline_result_keeps_original_question_type_and_section():
    """PipelineResult output preserves fine-grained type and section_id."""
    result = PipelineResult()
    result.sliced_questions = [
        SlicedQuestion(
            question_number="37",
            question_type="single_choice",
            original_question_type="seven_to_five",
            section_id="seven_to_five_1",
            stem="s",
            answer="B",
            confidence=0.9,
            issues=[],
        )
    ]

    d = result.to_dict()
    assert d["questions"][0]["original_question_type"] == "seven_to_five"
    assert d["questions"][0]["section_id"] == "seven_to_five_1"


def test_pipeline_result_ingest_lists():
    """PipelineResult 输出 ingested/discarded 双清单与 summary。"""
    result = PipelineResult()
    result.sliced_questions = [
        SlicedQuestion(
            question_number="1",
            question_type="single_choice",
            stem="s",
            answer="A",
            confidence=0.9,
            issues=[],
            structure_signature={
                "object": "函数",
                "task": "求值",
                "method": "代入法",
                "condition": "f(x)=x",
            },
        ),
        SlicedQuestion(
            question_number="2",
            question_type="single_choice",
            stem="",
            answer=None,
            confidence=0.6,
            issues=[
                "锚点需重新标注，禁止自动发布",
                "答案缺失，禁止自动发布",
            ],
        ),
    ]

    d = result.to_dict()
    assert d["ingest_summary"]["total"] == 2
    assert d["ingest_summary"]["ingested"] == 1
    assert d["ingest_summary"]["discarded"] == 1
    assert len(d["ingested_questions"]) == 1
    assert d["ingested_questions"][0]["structure_signature"] == {
        "object": "函数",
        "task": "求值",
        "method": "代入法",
        "condition": "f(x)=x",
    }
    assert len(d["discarded_questions"]) == 1
    assert "锚点不确定" in d["ingest_summary"]["discard_reasons"]
    assert "答案缺失" in d["ingest_summary"]["discard_reasons"]
    assert d["ingest_summary"]["discard_reasons"]["锚点不确定"] == 1
    assert d["ingest_summary"]["discard_reasons"]["答案缺失"] == 1
    assert "anchor_mismatch" in d["discarded_questions"][0]["discard_categories"]
    assert "answer_empty" in d["discarded_questions"][0]["discard_categories"]


@pytest.mark.asyncio
async def test_run_pipeline_mock():
    """Mock 模式下管线端到端运行。"""
    gateway = LLMGateway(
        mode="live",
        providers=[MockLLMProvider(response=_mock_llm_response())],
    )

    result = await run_pipeline(
        TEST_PDF,
        gateway=gateway,
        page_range=(1, 1),
    )

    assert result.total_time_ms > 0
    assert len(result.errors) == 0
    assert len(result.stages) >= 5
    assert result.l1_document is not None
    assert result.l2_annotation is not None
    assert len(result.sliced_questions) >= 1

    stage_names = [s["name"] for s in result.stages]
    assert "native_l1" in stage_names
    assert "llm_annotation" in stage_names
    assert "anchor_correction" in stage_names
    assert "content_slicing" in stage_names
    assert "answer_matching" in stage_names
    assert "quality_gate" in stage_names


@pytest.mark.asyncio
async def test_pipeline_has_confidence():
    """管线输出的每题有 confidence。"""
    gateway = LLMGateway(
        mode="live",
        providers=[MockLLMProvider(response=_mock_llm_response())],
    )

    result = await run_pipeline(
        TEST_PDF,
        gateway=gateway,
        page_range=(1, 1),
    )

    for sq in result.sliced_questions:
        assert hasattr(sq, "confidence")
        assert 0.0 <= sq.confidence <= 1.0
        assert hasattr(sq, "issues")
        assert isinstance(sq.issues, list)

def test_pipeline_result_serializes_nested_sub_questions():
    """PipelineResult.to_dict serializes recursive sub_questions."""
    result = PipelineResult()
    result.sliced_questions = [
        SlicedQuestion(
            question_number="1",
            question_type="short_answer",
            original_question_type="short_answer",
            stem="s",
            answer="(3) ok",
            confidence=0.9,
            issues=[],
            sub_questions=[
                L2SubQuestion(
                    qno="(3)",
                    question_type="short_answer",
                    sub_sub_questions=[
                        L2SubQuestion(qno="i", question_type="short_answer", answer="x"),
                    ],
                )
            ],
        )
    ]
    d = result.to_dict()
    nested = d["questions"][0]["sub_questions"][0]["sub_sub_questions"][0]
    assert nested["qno"] == "i"
    assert nested["answer"] == "x"

def test_pipeline_result_empty_nested_sub_questions_serialized_as_none():
    """Empty [] sub_sub_questions are normalized to None in output."""
    result = PipelineResult()
    result.sliced_questions = [
        SlicedQuestion(
            question_number="1",
            question_type="short_answer",
            stem="s",
            answer="x",
            confidence=0.9,
            issues=[],
            sub_questions=[L2SubQuestion(qno="a", sub_sub_questions=[])],
        )
    ]
    d = result.to_dict()
    assert d["questions"][0]["sub_questions"][0]["sub_sub_questions"] is None


def test_pipeline_result_serializes_three_level_sub_questions():
    """Three levels of nested sub-questions survive serialization."""
    result = PipelineResult()
    result.sliced_questions = [
        SlicedQuestion(
            question_number="1",
            question_type="short_answer",
            stem="s",
            answer="x",
            confidence=0.9,
            issues=[],
            sub_questions=[
                L2SubQuestion(
                    qno="a",
                    sub_sub_questions=[
                        L2SubQuestion(
                            qno="b",
                            sub_sub_questions=[L2SubQuestion(qno="c", answer="leaf")],
                        )
                    ],
                )
            ],
        )
    ]
    d = result.to_dict()
    leaf = d["questions"][0]["sub_questions"][0]["sub_sub_questions"][0]["sub_sub_questions"][0]
    assert leaf["qno"] == "c"
    assert leaf["answer"] == "leaf"

def test_pipeline_result_serializes_answer_structure():
    """PipelineResult.to_dict preserves answer_structure metadata."""
    result = PipelineResult()
    result.sliced_questions = [
        SlicedQuestion(
            question_number="1",
            question_type="short_answer",
            stem="s",
            answer="24.00~25.00",
            answer_structure={"range": {"min": "24.00", "max": "25.00"}},
            confidence=0.9,
            issues=[],
        )
    ]
    d = result.to_dict()
    assert d["questions"][0]["answer_structure"] == {"range": {"min": "24.00", "max": "25.00"}}

def test_pipeline_result_serializes_word_bank():
    """PipelineResult.to_dict preserves word_bank."""
    result = PipelineResult()
    result.sliced_questions = [
        SlicedQuestion(
            question_number="1",
            question_type="fill_in",
            stem="s",
            answer="confusing",
            confidence=0.9,
            issues=[],
            word_bank=["confuse", "pack"],
        )
    ]
    d = result.to_dict()
    assert d["questions"][0]["word_bank"] == ["confuse", "pack"]

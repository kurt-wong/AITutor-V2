"""文档处理管线单元测试。"""

import json
import pytest
from pathlib import Path

from app.ai.gateway import LLMGateway
from app.ai.providers import MockLLMProvider
from app.domains.document.pipeline import PipelineResult, run_pipeline

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

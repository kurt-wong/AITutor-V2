"""质量门单元测试。"""

from app.domains.document.quality_gate import evaluate_quality
from app.domains.document.schemas_l2 import SlicedQuestion, SourceProvenance


def test_high_quality_question():
    """高质量题目 confidence >= 0.8。"""
    questions = [
        SlicedQuestion(
            question_number="1",
            question_type="single_choice",
            stem="test question",
            options=[{"label": "A", "text": "1"}, {"label": "B", "text": "2"},
                     {"label": "C", "text": "3"}, {"label": "D", "text": "4"}],
            answer="A",
            answer_provenance=SourceProvenance("answer", "document_answer_table", 1.0),
            explanation="explanation",
            explanation_provenance=SourceProvenance("explanation", "document_inline_explanation", 1.0),
        ),
    ]

    result = evaluate_quality(questions)
    assert result[0].confidence >= 0.8
    assert len(result[0].issues) == 0


def test_empty_stem_lowers_confidence():
    """空题干降低 confidence。"""
    questions = [
        SlicedQuestion(
            question_number="1",
            question_type="single_choice",
            stem="",
            options=[],
        ),
    ]

    result = evaluate_quality(questions)
    assert result[0].confidence < 0.8
    assert "题干为空" in result[0].issues


def test_missing_options_lowers_confidence():
    """选项不足降低 confidence。"""
    questions = [
        SlicedQuestion(
            question_number="1",
            question_type="single_choice",
            stem="test",
            options=[{"label": "A", "text": "1"}, {"label": "B", "text": "2"}],
        ),
    ]

    result = evaluate_quality(questions)
    assert result[0].confidence < 1.0
    assert any("选项数量不足" in i for i in result[0].issues)


def test_llm_fallback_answer():
    """LLM 兜底答案降低 confidence。"""
    questions = [
        SlicedQuestion(
            question_number="1",
            question_type="single_choice",
            stem="test",
            options=[{"label": "A", "text": "1"}],
            answer_provenance=SourceProvenance("answer", "llm_fallback", 0.5),
        ),
    ]

    result = evaluate_quality(questions)
    assert result[0].confidence < 1.0
    assert any("LLM 兜底" in i for i in result[0].issues)


def test_fill_blank_no_options_issue():
    """填空题不检查选项数量。"""
    questions = [
        SlicedQuestion(
            question_number="1",
            question_type="fill_blank",
            stem="test",
            options=[],
        ),
    ]

    result = evaluate_quality(questions)
    assert not any("选项" in i for i in result[0].issues)


def test_zero_options_blocked():
    """单选题 0 个选项 -> 禁止自动发布。"""
    from app.domains.document.schemas_l2 import CorrectedAnchor
    questions = [
        SlicedQuestion(
            question_number="1",
            question_type="single_choice",
            stem="test",
            options=[],
            options_anchor=CorrectedAnchor(
                field="options",
                llm_line_ids=[],
                corrected_line_ids=[],
                anchor_status="missing",
            ),
        ),
    ]

    result = evaluate_quality(questions)
    assert result[0].confidence < 0.5
    assert any("禁止自动发布" in i for i in result[0].issues)


def test_anchor_status_missing_blocked():
    """锚点 missing -> 禁止自动发布。"""
    from app.domains.document.schemas_l2 import CorrectedAnchor
    questions = [
        SlicedQuestion(
            question_number="1",
            question_type="single_choice",
            stem="test",
            options=[{"label": "A", "text": "1"}, {"label": "B", "text": "2"},
                     {"label": "C", "text": "3"}, {"label": "D", "text": "4"}],
            stem_anchor=CorrectedAnchor(
                field="stem",
                llm_line_ids=[],
                corrected_line_ids=[],
                anchor_status="missing",
            ),
        ),
    ]

    result = evaluate_quality(questions)
    assert result[0].confidence < 0.8
    assert any("禁止自动发布" in i for i in result[0].issues)

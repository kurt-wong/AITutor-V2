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


def test_llm_annotation_empty_or_punctuation_answer_blocked():
    """LLM 行号切片为空或仅标点时必须禁止自动发布。"""
    questions = [
        SlicedQuestion(
            question_number="1",
            question_type="single_choice",
            stem="test",
            options=[{"label": "A", "text": "1"}, {"label": "B", "text": "2"},
                     {"label": "C", "text": "3"}, {"label": "D", "text": "4"}],
            answer="。",
            answer_line_ids=["P1L003"],
            answer_provenance=SourceProvenance("answer", "llm_annotation", 0.9),
        ),
    ]

    result = evaluate_quality(questions)
    assert any("LLM 答案切片为空或仅标点" in i for i in result[0].issues)
    assert any("禁止自动发布" in i for i in result[0].issues)


def test_llm_annotation_missing_answer_line_ids_blocked():
    """LLM 答案来源缺少 answer_line_ids 时必须禁止自动发布。"""
    questions = [
        SlicedQuestion(
            question_number="1",
            question_type="single_choice",
            stem="test",
            options=[{"label": "A", "text": "1"}, {"label": "B", "text": "2"},
                     {"label": "C", "text": "3"}, {"label": "D", "text": "4"}],
            answer="A",
            answer_line_ids=[],
            answer_provenance=SourceProvenance("answer", "llm_annotation", 0.9),
        ),
    ]

    result = evaluate_quality(questions)
    assert any("LLM 答案缺少有效行号" in i for i in result[0].issues)
    assert any("禁止自动发布" in i for i in result[0].issues)


def test_seven_choice_five_section_allows_seven_options():
    """七选五固定 7 个选项，不应被当作单选 4 项而报选项过多。"""
    questions = [
        SlicedQuestion(
            question_number="37",
            question_type="single_choice",
            section_id="七选五_1",
            stem="shared passage",
            options=[
                {"label": label, "text": str(i)}
                for i, label in enumerate("ABCDEFG", 1)
            ],
            answer="B",
            answer_provenance=SourceProvenance("answer", "document_answer_table", 1.0),
        ),
    ]

    result = evaluate_quality(questions)
    assert not any("选项数量过多" in i for i in result[0].issues)
    assert result[0].confidence >= 0.8


def test_composite_choice_group_skips_option_check():
    """综合题（共享题图选择题组）父题无选项 → 跳过选项检查。

    2026-08-26 育英地理"读图完成 18-20 题"：选择题组合并为综合题后，
    父题 question_type=single_choice 但 options=[]（子题选项在
    sub_questions 里）。quality_gate 不应要求父题有选项。
    """
    from app.domains.document.schemas_l2 import L2SubQuestion
    questions = [
        SlicedQuestion(
            question_number="18",
            question_type="single_choice",
            stem="读图，完成18—20题。\n材料行1\n材料行2",
            options=[],  # 综合题父题无独立选项
            answer="(18) B (19) A (20) B",
            answer_provenance=SourceProvenance("answer", "document_answer_table", 1.0),
            is_composite=True,
            sub_questions=[
                L2SubQuestion(qno="18", question_type="single_choice", answer="B",
                              options_line_ids={"A": ["P1L001"], "B": ["P1L002"]}),
                L2SubQuestion(qno="19", question_type="single_choice", answer="A",
                              options_line_ids={"A": ["P1L003"], "B": ["P1L004"]}),
                L2SubQuestion(qno="20", question_type="single_choice", answer="B",
                              options_line_ids={"A": ["P1L005"], "B": ["P1L006"]}),
            ],
        ),
    ]

    result = evaluate_quality(questions)
    assert not any("选项锚点缺失" in i for i in result[0].issues)
    assert not any("选项数量不足" in i for i in result[0].issues)


def test_non_composite_choice_still_requires_options():
    """非综合题选择题仍要求选项（回归保护）。"""
    questions = [
        SlicedQuestion(
            question_number="1",
            question_type="single_choice",
            stem="test",
            options=[],
            answer="A",
            answer_provenance=SourceProvenance("answer", "document_answer_table", 1.0),
            is_composite=False,
        ),
    ]

    result = evaluate_quality(questions)
    assert any("选项锚点缺失" in i for i in result[0].issues)

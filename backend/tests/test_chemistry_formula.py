"""P0-5 chemistry formula normalization tests."""
from app.domains.document.chemistry_formula import (
    normalize_chemistry_formula,
    normalize_chemistry_question,
)
from app.domains.document.schemas_l2 import L2SubQuestion, SlicedQuestion


def test_parenthesized_subscripts_standardized():
    assert normalize_chemistry_formula("Cl(2)") == "Cl₂"
    assert normalize_chemistry_formula("Fe(2)O(3)") == "Fe₂O₃"
    assert normalize_chemistry_formula("NaN(3)") == "NaN₃"
    assert normalize_chemistry_formula("CO(2)") == "CO₂"


def test_ion_charges_standardized():
    assert normalize_chemistry_formula("OH(﹣)") == "OH⁻"
    assert normalize_chemistry_formula("Fe(3+)") == "Fe³⁺"
    assert normalize_chemistry_formula("SO(4)(2-)") == "SO₄²⁻"
    assert normalize_chemistry_formula("NH(4)(+)") == "NH₄⁺"


def test_compound_group_subscripts_standardized():
    assert normalize_chemistry_formula("Mg(OH)(2)") == "Mg(OH)₂"
    assert normalize_chemistry_formula("Ca(OH)(2)") == "Ca(OH)₂"
    assert normalize_chemistry_formula("Cu(2)(OH)(2)CO(3)") == "Cu₂(OH)₂CO₃"
    assert normalize_chemistry_formula("Al(OH)(3)") == "Al(OH)₃"
    assert normalize_chemistry_formula("Fe(OH)(3)") == "Fe(OH)₃"


def test_question_number_not_treated_as_formula():
    text = "（1）下列叙述正确的是：Cl(2)+2OH(﹣)"
    assert normalize_chemistry_formula(text) == "（1）下列叙述正确的是：Cl₂+2OH⁻"


def test_question_fields_normalized_recursively():
    sq = SlicedQuestion(
        question_number="1",
        question_type="short_answer",
        stem="Cl(2)+2OH(﹣)",
        answer="Fe(3+)",
        explanation="Fe(2)O(3)",
        options=[{"label": "A", "text": "NaN(3)"}],
        sub_questions=[
            L2SubQuestion(
                qno="(1)",
                stem="CO(2)",
                answer="SO(4)(2-)",
                options=[{"label": "B", "text": "NH(4)(+)"}],
            )
        ],
    )
    normalize_chemistry_question(sq)
    assert sq.stem == "Cl₂+2OH⁻"
    assert sq.answer == "Fe³⁺"
    assert sq.explanation == "Fe₂O₃"
    assert sq.options[0]["text"] == "NaN₃"
    assert sq.sub_questions[0].stem == "CO₂"
    assert sq.sub_questions[0].answer == "SO₄²⁻"
    assert sq.sub_questions[0].options[0]["text"] == "NH₄⁺"

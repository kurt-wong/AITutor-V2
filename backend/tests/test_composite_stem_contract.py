"""Regression tests for composite container stem contract (DISPLAY_CONTRACT v0.5)."""

from app.domains.document.content_slicer import slice_questions
from app.domains.document.line_annotator import _build_wordbank_composite
from app.domains.document.schemas_l1 import L1Document, L1Line, L1Page
from app.domains.document.schemas_l2 import (
    CorrectedAnchor,
    L2DocumentAnnotation,
    L2QuestionAnnotation,
    L2SubQuestion,
)


def _doc(lines: list[L1Line]) -> L1Document:
    return L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source="ppsv3",
        total_pages=1,
    )


def _line(line_id: str, text: str, order: int) -> L1Line:
    return L1Line(
        line_id=line_id,
        page_no=1,
        line_no_in_page=order,
        order=order,
        text=text,
        block_type="text",
    )


def test_composite_stem_uses_task_instruction_only():
    """综合题容器 stem 不应把 shared_material 拼进 stem。"""
    lines = [
        _line("P1L001", "第一节（共1小题）阅读短文并作答。", 1),
        _line("P1L002", "The Ultimate Goal\nI sat in the dressing room.", 2),
        _line("P1L003", "1. What was the writer's goal?", 3),
    ]
    doc = _doc(lines)
    anchor = CorrectedAnchor(
        field="stem",
        llm_line_ids=["P1L001"],
        corrected_line_ids=["P1L001"],
        anchor_status="exact",
        validation_passed=True,
        question_number="1",
    )
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        subject="英语",
        questions=[
            L2QuestionAnnotation(
                question_number="1",
                question_type="short_answer",
                stem_line_ids=["P1L001"],
                shared_material_line_ids=["P1L002"],
                is_composite=True,
                sub_questions=[
                    L2SubQuestion(qno="1", question_type="short_answer", answer="To perform."),
                ],
            )
        ],
        corrected_anchors=[anchor],
    )

    sliced = slice_questions(annotation, doc)

    assert len(sliced) == 1
    sq = sliced[0]
    assert sq.stem == "第一节（共〔1〕小题）阅读短文并作答。"
    assert "The Ultimate Goal" not in sq.stem
    assert sq.stem_line_ids == ["P1L001"]
    assert sq.shared_material == "The Ultimate Goal\nI sat in the dressing room."


def test_wordbank_composite_uses_instruction_and_wordbank_lines():
    """选词填空容器 stem/shared_material 应按展示契约拆分。"""
    lines = [
        _line("P1L001", "A. 请用方框中的单词完成句子。", 1),
        _line("P1L002", "（本题见校本卷）", 2),
        _line("P1L003", "B. 请用方框中单词的正确形式完成句子。", 3),
        _line("P1L004", "pack confuse equal contribute athlete", 4),
        _line("P1L005", "21. Thank you for trying to give me directions.", 5),
        _line("P1L006", "22. Jim is a young boy who is strong.", 6),
    ]
    doc = _doc(lines)
    q1 = L2QuestionAnnotation(
        question_number="21",
        question_type="fill_in",
        section_id="选词填空_1",
        stem_line_ids=["P1L005"],
        answer="confusing",
    )
    q2 = L2QuestionAnnotation(
        question_number="22",
        question_type="fill_in",
        section_id="选词填空_1",
        stem_line_ids=["P1L006"],
        answer="athletic",
    )

    composite = _build_wordbank_composite([q1, q2], doc)

    assert composite.stem_line_ids == ["P1L001", "P1L002", "P1L003"]
    assert composite.shared_material_line_ids == [
        "P1L001",
        "P1L002",
        "P1L003",
        "P1L004",
    ]
    assert len(composite.sub_questions) == 2
    assert composite.sub_questions[0].answer == "confusing"
    assert composite.sub_questions[1].answer == "athletic"

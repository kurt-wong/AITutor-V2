"""对抗性审查：P1-6 子题答案提取的边界条件。"""
from app.domains.document.content_slicer import _merge_question_group
from app.domains.document.schemas_l1 import L1Document, L1Line, L1Page
from app.domains.document.schemas_l2 import CorrectedAnchor, L2SubQuestion, SlicedQuestion


def _doc():
    lines = [
        L1Line("P1L001", 1, 1, 1, "材料行1", "text"),
        L1Line("P1L002", 1, 2, 2, "1. 第一空", "text"),
    ]
    return L1Document(
        filename="t.pdf", pages=[L1Page(page_no=1, lines=lines)],
        lines=lines, source="ppsv3", total_pages=1,
    )


def _q(qno, l2_subs=None, sliced_answer=None):
    anchor = CorrectedAnchor(
        field="stem", llm_line_ids=[f"P1L00{int(qno)}"],
        corrected_line_ids=[f"P1L00{int(qno)}"],
        anchor_status="exact", validation_passed=True,
    )
    return SlicedQuestion(
        question_number=qno, question_type="fill_in", stem="", options=[],
        answer=sliced_answer, confidence=0.9,
        stem_anchor=anchor, corrected_anchors=[anchor],
        shared_material_line_ids=["P1L001"],
        sub_questions=l2_subs,
    )


class TestP16Adversarial:
    def test_l2_sub_with_empty_answer_falls_through(self):
        doc = _doc()
        lid = {l.line_id: l for l in doc.lines}
        q = _q("1", l2_subs=[L2SubQuestion(qno="1", answer=None, question_type="fill_in")])
        merged = _merge_question_group([q], lid)
        assert merged.answer is None

    def test_mixed_l2_and_no_l2_in_group(self):
        doc = _doc()
        lid = {l.line_id: l for l in doc.lines}
        q1 = _q("1", l2_subs=[L2SubQuestion(qno="1", answer="X")])
        q2 = _q("2", sliced_answer="Y")
        merged = _merge_question_group([q1, q2], lid)
        assert merged.answer is not None
        assert "X" in merged.answer
        assert "Y" in merged.answer

    def test_l2_sub_with_multiple_blanks(self):
        doc = _doc()
        lid = {l.line_id: l for l in doc.lines}
        subs = [
            L2SubQuestion(qno="1", answer="A"),
            L2SubQuestion(qno="2", answer="B"),
            L2SubQuestion(qno="3", answer="C"),
        ]
        q = _q("1", l2_subs=subs)
        merged = _merge_question_group([q], lid)
        assert len(merged.sub_questions) == 3
        assert merged.answer is not None
        assert "A" in merged.answer and "B" in merged.answer and "C" in merged.answer

    def test_single_question_group_still_works(self):
        doc = _doc()
        lid = {l.line_id: l for l in doc.lines}
        q = _q("1", l2_subs=[L2SubQuestion(qno="1", answer="X")])
        merged = _merge_question_group([q], lid)
        assert merged.sub_questions is not None

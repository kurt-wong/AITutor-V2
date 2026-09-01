"""P1-6 严格测试：综合题子题答案从 L2 标注层正确提取。

审计发现（bugs.md BUG-012 §二 E）：
- _merge_question_group 用 q.answer（SlicedQuestion.answer，永远 None）构建子题元数据 →
  子题答案全部丢失，merged_answer 也为空。
- 修复：从 q.sub_questions（L2 标注层，带 LLM 输出的答案）提取。

本测试验证：
1. L2 子题有答案时正确传递到合并后的 sub_questions
2. merged_answer 由子题答案正确构建
3. 无 L2 子题时回退到 SlicedQuestion.answer
"""

from app.domains.document.content_slicer import (
    _merge_question_group,
    slice_questions,
)
from app.domains.document.schemas_l1 import L1Document, L1Line, L1Page
from app.domains.document.schemas_l2 import (
    CorrectedAnchor,
    L2DocumentAnnotation,
    L2QuestionAnnotation,
    L2SubQuestion,
    SlicedQuestion,
)


def _doc() -> L1Document:
    lines = [
        L1Line("P1L001", 1, 1, 1, "材料行1", "text"),
        L1Line("P1L002", 1, 2, 2, "材料行2", "text"),
        L1Line("P1L003", 1, 3, 3, "1. 第一空", "text"),
        L1Line("P1L004", 1, 4, 4, "2. 第二空", "text"),
    ]
    return L1Document(
        filename="test.pdf", pages=[L1Page(page_no=1, lines=lines)],
        lines=lines, source="ppsv3", total_pages=1,
    )


def _make_sub_q(qno: str, answer: str) -> SlicedQuestion:
    """构造带 L2 子题的 SlicedQuestion（模拟 _slice_single_question 输出）。"""
    anchor = CorrectedAnchor(
        field="stem", llm_line_ids=[f"P1L00{int(qno)}"],
        corrected_line_ids=[f"P1L00{int(qno)}"],
        anchor_status="exact", validation_passed=True,
    )
    return SlicedQuestion(
        question_number=qno,
        question_type="fill_in",
        stem="",
        options=[],
        answer=None,  # SlicedQuestion.answer 永远 None（_slice_single_question 不设置）
        confidence=0.9,
        stem_anchor=anchor,
        corrected_anchors=[anchor],
        shared_material_line_ids=["P1L001", "P1L002"],
        sub_questions=[L2SubQuestion(qno=qno, answer=answer, question_type="fill_in")],
    )


class TestMergeQuestionGroupSubQuestionAnswers:
    def test_l2_sub_answers_extracted(self):
        """L2 子题有答案时，合并后 sub_questions[i].answer 正确传递。"""
        doc = _doc()
        line_by_id = {l.line_id: l for l in doc.lines}
        group = [
            _make_sub_q("1", "A"),
            _make_sub_q("2", "B"),
        ]
        merged = _merge_question_group(group, line_by_id)

        answers = [sq.answer for sq in (merged.sub_questions or [])]
        assert "A" in answers
        assert "B" in answers

    def test_merged_answer_built_from_sub_answers(self):
        """merged_answer 由子题答案正确构建（非 None）。"""
        doc = _doc()
        line_by_id = {l.line_id: l for l in doc.lines}
        group = [
            _make_sub_q("1", "C"),
            _make_sub_q("2", "D"),
        ]
        merged = _merge_question_group(group, line_by_id)

        assert merged.answer is not None
        assert "C" in merged.answer
        assert "D" in merged.answer

    def test_no_l2_sub_fallback_to_sliced_question_answer(self):
        """无 L2 子题时回退到 SlicedQuestion.answer。"""
        doc = _doc()
        line_by_id = {l.line_id: l for l in doc.lines}
        anchor = CorrectedAnchor(
            field="stem", llm_line_ids=["P1L003"],
            corrected_line_ids=["P1L003"],
            anchor_status="exact", validation_passed=True,
        )
        q = SlicedQuestion(
            question_number="1", question_type="fill_in", stem="", options=[],
            answer="X",  # SlicedQuestion.answer 有值
            confidence=0.9, stem_anchor=anchor, corrected_anchors=[anchor],
            shared_material_line_ids=["P1L001"], sub_questions=None,  # 无 L2 子题
        )
        merged = _merge_question_group([q], line_by_id)
        assert merged.answer is not None
        assert "X" in merged.answer

    def test_choice_group_sub_options_preserved(self):
        """选择题组综合题（共享题图）：子题的 stem_line_ids/options_line_ids 透传。

        2026-08-26：育英地理"读图完成 18-20 题"共享题图选择题组，LLM 输出
        综合题子题带各自题干/选项行号 → _merge_question_group 必须保留，
        否则合并后子题丢失选项（无法独立展示）。
        """
        doc = _doc()
        line_by_id = {l.line_id: l for l in doc.lines}
        anchor = CorrectedAnchor(
            field="stem", llm_line_ids=["P1L003"],
            corrected_line_ids=["P1L003"],
            anchor_status="exact", validation_passed=True,
        )
        q1 = SlicedQuestion(
            question_number="18", question_type="single_choice", stem="", options=[],
            answer=None, confidence=0.9, stem_anchor=anchor, corrected_anchors=[anchor],
            shared_material_line_ids=["P1L001", "P1L002"],
            sub_questions=[L2SubQuestion(
                qno="18", question_type="single_choice", answer="D",
                stem_line_ids=["P1L003"],
                options_line_ids={"A": ["P1L004"], "B": ["P1L005"]},
            )],
        )
        q2 = SlicedQuestion(
            question_number="19", question_type="single_choice", stem="", options=[],
            answer=None, confidence=0.9, stem_anchor=anchor, corrected_anchors=[anchor],
            shared_material_line_ids=["P1L001", "P1L002"],
            sub_questions=[L2SubQuestion(
                qno="19", question_type="single_choice", answer="B",
                stem_line_ids=["P1L004"],
                options_line_ids={"A": ["P1L006"], "B": ["P1L007"]},
            )],
        )
        merged = _merge_question_group([q1, q2], line_by_id)
        assert merged.is_composite is True
        assert len(merged.sub_questions) == 2
        # 子题选项透传
        sub_opts = {s.qno: s.options_line_ids for s in (merged.sub_questions or [])}
        assert sub_opts["18"] == {"A": ["P1L004"], "B": ["P1L005"]}
        assert sub_opts["19"] == {"A": ["P1L006"], "B": ["P1L007"]}
        # 子题题干行号透传
        sub_stems = {s.qno: s.stem_line_ids for s in (merged.sub_questions or [])}
        assert sub_stems["18"] == ["P1L003"]
        assert sub_stems["19"] == ["P1L004"]


def test_slice_questions_builds_parent_answer_from_subs():
    """LLM 直接输出的综合题：父题 answer 为空时从子题答案汇总构建。

    2026-08-26：育英地理共享题图选择题组，LLM 把答案写在 sub_questions[].answer
    （父题 answer 字段为空）。slice_questions 必须在切片阶段为综合题父题
    构建子题答案汇总（"(1) C (2) B ..." 格式），否则 answer_matcher 的
    纯字母校验清空后父题 answer=None → quality_gate 误报 answer_missing。
    """
    lines = [
        L1Line("P1L001", 1, 1, 1, "读图，完成9—11题", "text"),
        L1Line("P1L002", 1, 2, 2, "（A）选项", "text"),
        L1Line("P1L003", 1, 3, 3, "（B）选项", "text"),
    ]
    doc = L1Document(
        filename="test.pdf", pages=[L1Page(page_no=1, lines=lines)],
        lines=lines, source="native", total_pages=1,
    )
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[L2QuestionAnnotation(
            question_number="9",
            question_type="single_choice",
            stem_line_ids=["P1L001"],
            shared_material_line_ids=["P1L001"],
            is_composite=True,
            answer=None,  # LLM 父题 answer 为空
            sub_questions=[
                L2SubQuestion(qno="9", question_type="single_choice", answer="A"),
                L2SubQuestion(qno="10", question_type="single_choice", answer="B"),
                L2SubQuestion(qno="11", question_type="single_choice", answer="D"),
            ],
        )],
    )

    sliced = slice_questions(annotation, doc)
    assert len(sliced) == 1
    assert sliced[0].is_composite is True
    # 容器不应有答案（答案只在子题中）
    assert sliced[0].answer is None
    # 子题答案保留
    assert sliced[0].sub_questions[0].answer == "A"
    assert sliced[0].sub_questions[1].answer == "B"
    assert sliced[0].sub_questions[2].answer == "D"


def test_slice_questions_keeps_existing_parent_answer():
    """综合题父题已有答案（如解答题从答案表匹配）时不覆盖。"""
    lines = [
        L1Line("P1L001", 1, 1, 1, "阅读材料", "text"),
        L1Line("P1L002", 1, 2, 2, "（1）第一问", "text"),
    ]
    doc = L1Document(
        filename="test.pdf", pages=[L1Page(page_no=1, lines=lines)],
        lines=lines, source="native", total_pages=1,
    )
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[L2QuestionAnnotation(
            question_number="26",
            question_type="short_answer",
            stem_line_ids=["P1L001"],
            shared_material_line_ids=["P1L001"],
            is_composite=True,
            answer="（1）已有答案",  # 父题已有答案
            sub_questions=[
                L2SubQuestion(qno="（1）", question_type="short_answer", answer="子题答案"),
            ],
        )],
    )

    sliced = slice_questions(annotation, doc)
    assert len(sliced) == 1
    # 容器不应有答案（即使 LLM 输出了容器答案）
    assert sliced[0].answer is None
    # 子题答案保留
    assert sliced[0].sub_questions[0].answer == "子题答案"

def test_merge_question_group_keeps_original_question_type():
    """Merged composite keeps the first question fine-grained type."""
    doc = _doc()
    line_by_id = {l.line_id: l for l in doc.lines}
    q1 = _make_sub_q("1", "A")
    q1.original_question_type = "cloze"
    q2 = _make_sub_q("2", "B")
    q2.original_question_type = "cloze"
    merged = _merge_question_group([q1, q2], line_by_id)
    assert merged.original_question_type == "cloze"

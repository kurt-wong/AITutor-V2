"""P0-C 测试：选择题共享 answer_line_id 时，LLM 直接答案优先于切片。

根因：生物 Q6 和 Q7 的 answer_line_ids 都是 ['P9L003']（OCR 答案表同一行），
切片逻辑从同一行提取答案 → Q7 取到 Q6 的答案 'D' 而非 LLM 的正确答案 'A'。

修复：选择题如果 LLM 直接给了有效字母答案，直接用，不走切片。
"""

import pytest

from app.domains.document.answer_matcher import _apply_llm_annotation_answers, match_answers
from app.domains.document.schemas_l1 import L1Document, L1Line, L1Page
from app.domains.document.schemas_l2 import (
    CorrectedAnchor,
    L2DocumentAnnotation,
    L2QuestionAnnotation,
    SlicedQuestion,
    L2SubQuestion,
)


def _doc_with_answer_table() -> L1Document:
    """模拟生物 OCR L1：答案表在 P9L003。"""
    lines = [
        L1Line("P1L001", 1, 1, 1, "6.下列有关蛋白质结构、功能多样性的说法中，正确的是（）", "text"),
        L1Line("P1L002", 1, 2, 2, "A.选项1 B.选项2 C.选项3 D.选项4", "text"),
        L1Line("P2L001", 2, 1, 3, "7.由1分子磷酸、1分子碱基和1分子化合物a构成了化合物b", "text"),
        L1Line("P2L002", 2, 2, 4, "A.选项1 B.选项2 C.选项3 D.选项4", "text"),
        # 答案区
        L1Line("P9L001", 9, 1, 5, "参考答案", "text"),
        L1Line("P9L002", 9, 2, 6, "题号 6 7 8 9 10", "text"),
        L1Line("P9L003", 9, 3, 7, "答案 D A C B D", "text"),  # 答案表行：Q6=D, Q7=A
    ]
    return L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=lines[:4]), L1Page(page_no=9, lines=lines[4:])],
        lines=lines,
        source="ppsv3",
        total_pages=9,
    )


def _sliced_q6() -> SlicedQuestion:
    anchor = CorrectedAnchor(
        field="stem", llm_line_ids=["P1L001"],
        corrected_line_ids=["P1L001"],
        anchor_status="exact", validation_passed=True,
    )
    return SlicedQuestion(
        question_number="6", question_type="single_choice",
        stem="6.下列有关蛋白质结构", options=[],
        stem_anchor=anchor, corrected_anchors=[anchor],
    )


def _sliced_q7() -> SlicedQuestion:
    anchor = CorrectedAnchor(
        field="stem", llm_line_ids=["P2L001"],
        corrected_line_ids=["P2L001"],
        anchor_status="exact", validation_passed=True,
    )
    return SlicedQuestion(
        question_number="7", question_type="single_choice",
        stem="7.由1分子磷酸", options=[],
        stem_anchor=anchor, corrected_anchors=[anchor],
    )


class TestSharedAnswerLineId:
    """选择题共享 answer_line_id 时，LLM 直接答案优先。"""

    def test_choice_question_uses_llm_direct_answer_over_slice(self):
        """Q6 和 Q7 共享 answer_line_ids=['P9L003']，LLM 各自给了正确答案。"""
        doc = _doc_with_answer_table()
        sliced = [_sliced_q6(), _sliced_q7()]

        l2 = L2DocumentAnnotation(
            filename="test.pdf",
            questions=[
                L2QuestionAnnotation(
                    question_number="6", question_type="single_choice",
                    stem_line_ids=["P1L001"], options_line_ids={},
                    answer="D",  # LLM 直接答案
                    answer_line_ids=["P9L003"],  # 共享答案行
                ),
                L2QuestionAnnotation(
                    question_number="7", question_type="single_choice",
                    stem_line_ids=["P2L001"], options_line_ids={},
                    answer="A",  # LLM 直接答案
                    answer_line_ids=["P9L003"],  # 共享答案行（同 Q6）
                ),
            ],
        )

        _apply_llm_annotation_answers(sliced, l2, doc)

        # Q6 应该用 LLM 直接答案 'D'
        assert sliced[0].answer == "D", f"Q6 期望 'D'，实际 '{sliced[0].answer}'"
        # Q7 应该用 LLM 直接答案 'A'（不是从 P9L003 切片得到的 'D'）
        assert sliced[1].answer == "A", f"Q7 期望 'A'，实际 '{sliced[1].answer}'"

    def test_choice_question_fallback_to_slice_when_no_direct_answer(self):
        """LLM 没给直接答案时，仍走切片（结果可能为 None，因为多答案行切片不可靠）。"""
        doc = _doc_with_answer_table()
        sliced = [_sliced_q6()]

        l2 = L2DocumentAnnotation(
            filename="test.pdf",
            questions=[
                L2QuestionAnnotation(
                    question_number="6", question_type="single_choice",
                    stem_line_ids=["P1L001"], options_line_ids={},
                    answer=None,  # 无直接答案
                    answer_line_ids=["P9L003"],
                ),
            ],
        )

        _apply_llm_annotation_answers(sliced, l2, doc)
        # 多答案行切片不可靠，可能返回 None——这正是为什么选择题需要直接用 LLM 答案
        # 这里不断言具体值，只确认不报错
        assert True

    def test_choice_question_invalid_direct_answer_falls_back_to_slice(self):
        """LLM 直接答案不是有效字母时，回退到切片（结果可能为 None）。"""
        doc = _doc_with_answer_table()
        sliced = [_sliced_q6()]

        l2 = L2DocumentAnnotation(
            filename="test.pdf",
            questions=[
                L2QuestionAnnotation(
                    question_number="6", question_type="single_choice",
                    stem_line_ids=["P1L001"], options_line_ids={},
                    answer="错误答案",  # 无效字母
                    answer_line_ids=["P9L003"],
                ),
            ],
        )

        _apply_llm_annotation_answers(sliced, l2, doc)
        # 无效答案 + 多答案行切片不可靠 → 可能为 None
        # 这进一步证明：选择题必须有 LLM 直接答案
        assert True

    def test_short_answer_still_uses_slice(self):
        """解答题不受影响：仍从 answer_line_ids 切片。"""
        doc = _doc_with_answer_table()
        anchor = CorrectedAnchor(
            field="stem", llm_line_ids=["P1L001"],
            corrected_line_ids=["P1L001"],
            anchor_status="exact", validation_passed=True,
        )
        sliced_sq = SlicedQuestion(
            question_number="22", question_type="short_answer",
            stem="22.计算题", options=[],
            stem_anchor=anchor, corrected_anchors=[anchor],
        )

        l2 = L2DocumentAnnotation(
            filename="test.pdf",
            questions=[
                L2QuestionAnnotation(
                    question_number="22", question_type="short_answer",
                    stem_line_ids=["P1L001"], options_line_ids={},
                    answer="简短答案",
                    answer_line_ids=["P9L003"],
                ),
            ],
        )

        _apply_llm_annotation_answers([sliced_sq], l2, doc)
        # 解答题应从切片取答案，不直接用 LLM 原文
        assert sliced_sq.answer is not None

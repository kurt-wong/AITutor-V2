"""回归测试 — word-bank 合并路径保留展示契约字段。

验证 _merge_wordbank_fill_composites 和 _build_wordbank_composite
在合并选词填空小题时，不会丢失子题的展示契约字段。
"""

import pytest

from app.domains.document.line_annotator import (
    _build_wordbank_composite,
    _merge_wordbank_fill_composites,
)
from app.domains.document.schemas_l1 import L1Document, L1Line
from app.domains.document.schemas_l2 import L2QuestionAnnotation, L2SubQuestion


def _make_doc(lines: list[tuple[str, str]]) -> L1Document:
    """创建测试文档。"""
    return L1Document(
        filename="test.pdf",
        lines=[
            L1Line(
                line_id=lid,
                page_no=1,
                line_no_in_page=i+1,
                order=i+1,
                text=text,
                block_type="text",
            )
            for i, (lid, text) in enumerate(lines)
        ],
    )


class TestWordbankCompositePreservesDisplayFields:
    """选词填空合并保留展示字段。"""

    def test_build_wordbank_composite_preserves_sub_fields(self):
        """_build_wordbank_composite 应保留子题和父题的展示契约字段。"""
        # 构造带展示字段的选词填空小题
        q1 = L2QuestionAnnotation(
            question_number="11",
            question_type="fill_in",
            section_id="选词填空_1",
            stem_line_ids=["P1L002"],
            answer="racing",
            answer_line_ids=["P2L001"],
            explanation_line_ids=["P3L001"],
            scoring_standard="每空1分",
            answer_images=[{"page_no": 2, "bbox": {"x1": 0, "y1": 0, "x2": 100, "y2": 100}}],
            difficulty=3,
        )
        q2 = L2QuestionAnnotation(
            question_number="12",
            question_type="fill_in",
            section_id="选词填空_1",
            stem_line_ids=["P1L003"],
            answer="dancing",
            answer_line_ids=["P2L002"],
            explanation_line_ids=["P3L002"],
            scoring_standard="每空1分",
            answer_images=[{"page_no": 3, "bbox": {"x1": 0, "y1": 0, "x2": 50, "y2": 50}}],
            difficulty=3,
        )

        doc = _make_doc([
            ("P1L001", "选词填空：用方框中单词的正确形式填空"),
            ("P1L002", "11. He enjoys ____ (race) cars."),
            ("P1L003", "12. She likes ____ (dance) very much."),
        ])

        # 合并
        result = _build_wordbank_composite([q1, q2], doc)

        # 验证容器（分组题头）
        assert result.is_composite is True
        assert result.question_number == "11"
        assert len(result.sub_questions) == 2
        # 容器应有评分标准
        assert result.scoring_standard == "每空1分"
        # 容器不应有答案类字段（答案只在子题中）
        assert result.answer is None
        assert result.answer_line_ids == []
        assert result.answer_images is None or result.answer_images == []
        assert result.explanation_line_ids == []

        # 验证子题1
        sub1 = result.sub_questions[0]
        assert sub1.qno == "11"
        assert sub1.answer == "racing"
        assert sub1.answer_line_ids == ["P2L001"]
        assert sub1.explanation_line_ids == ["P3L001"]
        assert sub1.scoring_standard == "每空1分"
        assert sub1.answer_images == [{"page_no": 2, "bbox": {"x1": 0, "y1": 0, "x2": 100, "y2": 100}}]

        # 验证子题2
        sub2 = result.sub_questions[1]
        assert sub2.qno == "12"
        assert sub2.answer == "dancing"
        assert sub2.answer_line_ids == ["P2L002"]
        assert sub2.explanation_line_ids == ["P3L002"]
        assert sub2.scoring_standard == "每空1分"
        assert sub2.answer_images == [{"page_no": 3, "bbox": {"x1": 0, "y1": 0, "x2": 50, "y2": 50}}]

    def test_merge_wordbank_fill_composites_preserves_fields(self):
        """_merge_wordbank_fill_composites 应保留子题展示字段。"""
        q1 = L2QuestionAnnotation(
            question_number="11",
            question_type="fill_in",
            section_id="选词填空_1",
            stem_line_ids=["P1L002"],
            answer="racing",
            answer_line_ids=["P2L001"],
            explanation_line_ids=["P3L001"],
            scoring_standard="每空1分",
            word_bank=["race", "dance", "sing"],
            difficulty=3,
        )
        q2 = L2QuestionAnnotation(
            question_number="12",
            question_type="fill_in",
            section_id="选词填空_1",
            stem_line_ids=["P1L003"],
            answer="dancing",
            answer_line_ids=["P2L002"],
            explanation_line_ids=["P3L002"],
            scoring_standard="每空1分",
            word_bank=["race", "dance", "sing"],
            difficulty=3,
        )

        doc = _make_doc([
            ("P1L001", "race, dance, sing"),
            ("P1L002", "11. He enjoys ____ (race) cars."),
            ("P1L003", "12. She likes ____ (dance) very much."),
        ])

        # 合并
        result = _merge_wordbank_fill_composites([q1, q2], doc)

        assert len(result) == 1
        merged = result[0]
        assert merged.is_composite is True
        assert len(merged.sub_questions) == 2

        # 验证子题字段保留
        sub1 = merged.sub_questions[0]
        assert sub1.answer_line_ids == ["P2L001"]
        assert sub1.explanation_line_ids == ["P3L001"]
        assert sub1.scoring_standard == "每空1分"

    def test_single_wordbank_question_preserves_fields(self):
        """单个选词填空题（不合并）也应保留展示字段。"""
        q = L2QuestionAnnotation(
            question_number="11",
            question_type="fill_in",
            section_id="选词填空_1",
            stem_line_ids=["P1L002"],
            answer="racing",
            answer_line_ids=["P2L001"],
            explanation_line_ids=["P3L001"],
            scoring_standard="每空1分",
            word_bank=["race", "dance"],
            difficulty=3,
        )

        doc = _make_doc([
            ("P1L001", "race, dance"),
            ("P1L002", "11. He enjoys ____ (race) cars."),
        ])

        # 不合并（只有1题）
        result = _merge_wordbank_fill_composites([q], doc)

        assert len(result) == 1
        assert result[0].answer_line_ids == ["P2L001"]
        assert result[0].explanation_line_ids == ["P3L001"]
        assert result[0].scoring_standard == "每空1分"

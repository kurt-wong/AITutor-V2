"""P0-B 测试：stem 结束位置校验 — 截断到下一题起点之前。

验证：
1. stem 包含下一题的行 → 被截断
2. stem 不包含下一题的行 → 不变
3. 综合题的 stem 截断逻辑正确
"""

import pytest
from app.domains.document.anchor_corrector import (
    _truncate_stem_at_next_question,
    _build_question_start_map,
)
from app.domains.document.schemas_l1 import L1Document, L1Line, L1Page


def _line(line_id: str, text: str, order: int, page_no: int = 1) -> L1Line:
    return L1Line(
        line_id=line_id, page_no=page_no, line_no_in_page=order,
        order=order, text=text, block_type="text",
        bbox={"x1": 0, "y1": 0, "x2": 100, "y2": 20},
        source="ppsv3",
    )


def _doc(lines: list[L1Line]) -> L1Document:
    return L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        images=[],
        source="ppsv3",
        total_pages=1,
    )


class TestTruncateStemAtNextQuestion:
    """P0-B: stem 行号截断到下一题起点。"""

    def test_stem_extending_past_next_question_is_truncated(self):
        """stem 包含下一题行 → 被截断到下一题之前。"""
        lines = [
            _line("P1L001", "1. Q1 stem start", 1),
            _line("P1L002", "Q1 continuation", 2),
            _line("P1L003", "2. Q2 stem start", 3),
            _line("P1L004", "Q2 continuation", 4),
        ]
        doc = _doc(lines)
        line_by_id = {l.line_id: l for l in lines}
        qmap = _build_question_start_map(doc)

        # Q1 stem 误标为包含 Q2 的行
        stem_ids = ["P1L001", "P1L002", "P1L003"]

        result = _truncate_stem_at_next_question(
            stem_ids, line_by_id, qmap, "1", float("inf"),
        )

        assert result == ["P1L001", "P1L002"], (
            f"P1L003 (Q2 start) 应被截断，实际 {result}"
        )

    def test_stem_not_extending_is_unchanged(self):
        """stem 不包含下一题行 → 不变。"""
        lines = [
            _line("P1L001", "1. Q1 stem", 1),
            _line("P1L002", "Q1 continuation", 2),
            _line("P1L003", "2. Q2 stem", 3),
        ]
        doc = _doc(lines)
        line_by_id = {l.line_id: l for l in lines}
        qmap = _build_question_start_map(doc)

        stem_ids = ["P1L001", "P1L002"]

        result = _truncate_stem_at_next_question(
            stem_ids, line_by_id, qmap, "1", float("inf"),
        )

        assert result == ["P1L001", "P1L002"]

    def test_last_question_uses_stop_order(self):
        """最后一题的边界是答案区起点（stop_order），不是无穷大。"""
        lines = [
            _line("P1L001", "10. Last question", 1),
            _line("P1L002", "Last continuation", 2),
            _line("P1L003", "参考答案", 3),
            _line("P1L004", "1. A  2. B", 4),
        ]
        doc = _doc(lines)
        line_by_id = {l.line_id: l for l in lines}
        qmap = _build_question_start_map(doc)

        # stem 包含答案区行
        stem_ids = ["P1L001", "P1L002", "P1L003"]

        result = _truncate_stem_at_next_question(
            stem_ids, line_by_id, qmap, "10", 3,  # stop_order=3
        )

        assert result == ["P1L001", "P1L002"], (
            f"P1L003 (答案区) 应被截断，实际 {result}"
        )

    def test_empty_stem_unchanged(self):
        """空 stem → 不变。"""
        lines = [_line("P1L001", "1. Q1", 1)]
        doc = _doc(lines)
        line_by_id = {l.line_id: l for l in lines}
        qmap = _build_question_start_map(doc)

        result = _truncate_stem_at_next_question(
            [], line_by_id, qmap, "1", float("inf"),
        )

        assert result == []

    def test_no_next_question_uses_stop_order(self):
        """没有下一题时，用 stop_order 做边界。"""
        lines = [
            _line("P1L001", "5. Only question", 1),
            _line("P1L002", "continuation", 2),
        ]
        doc = _doc(lines)
        line_by_id = {l.line_id: l for l in lines}
        qmap = _build_question_start_map(doc)

        stem_ids = ["P1L001", "P1L002"]

        # stop_order=inf, no next question → 不截断
        result = _truncate_stem_at_next_question(
            stem_ids, line_by_id, qmap, "5", float("inf"),
        )
        assert result == ["P1L001", "P1L002"]

        # stop_order=2 → 截断
        result = _truncate_stem_at_next_question(
            stem_ids, line_by_id, qmap, "5", 2,
        )
        assert result == ["P1L001"]

    def test_all_lines_past_boundary_returns_empty(self):
        """所有行都在下一题边界之后 → 返回空列表（不回退到原始列表）。

        对抗性验证：旧代码 `return truncated if truncated else stem_line_ids`
        会在 truncated 为空时返回原始列表，截断被静默撤销。
        """
        lines = [
            _line("P1L001", "1. Q1 start", 1),
            _line("P1L002", "2. Q2 start", 2),
            _line("P1L003", "Q2 continuation", 3),
        ]
        line_by_id = {l.line_id: l for l in lines}
        qmap = {1: "P1L001", 2: "P1L002"}

        # stem 只包含 Q2 的行（全部在 Q2 边界之后）
        stem_ids = ["P1L002", "P1L003"]

        result = _truncate_stem_at_next_question(
            stem_ids, line_by_id, qmap, "1", float("inf"),
        )

        assert result == [], (
            f"全部行在边界之后时应返回空列表，实际 {result}。"
            "如果返回原始列表，说明 fallback bug 仍在。"
        )


class TestCorrectAnchorsStemSync:
    """P0-B 集成测试：correct_anchors 截断后 stem_anchor.corrected_line_ids 同步。"""

    def test_correct_anchors_syncs_stem_anchor_after_truncation(self):
        """截断后 question.stem_line_ids 和 stem_anchor.corrected_line_ids 一致。"""
        from app.domains.document.anchor_corrector import correct_anchors
        from app.domains.document.schemas_l2 import (
            L2DocumentAnnotation,
            L2QuestionAnnotation,
        )

        lines = [
            _line("P1L001", "1. Q1 stem start", 1),
            _line("P1L002", "Q1 continuation", 2),
            _line("P1L003", "2. Q2 stem start", 3),
            _line("P1L004", "Q2 continuation", 4),
        ]
        doc = _doc(lines)

        # LLM 标注 Q1 stem 包含 P1L001-P1L003（含 Q2 的首行）
        q1 = L2QuestionAnnotation(
            question_number="1",
            question_type="single_choice",
            stem_line_ids=["P1L001", "P1L002", "P1L003"],
            options_line_ids={"A": ["P1L004"]},
            answer_line_ids=[],
            explanation_line_ids=[],
            is_composite=False,
        )
        annotation = L2DocumentAnnotation(
            filename="test.pdf",
            questions=[q1],
        )

        result = correct_anchors(annotation, doc)

        # 截断后 stem_line_ids 应不含 P1L003（Q2 start）
        assert result.questions[0].stem_line_ids == ["P1L001", "P1L002"], (
            f"stem_line_ids 应截断到 Q2 之前，实际 {result.questions[0].stem_line_ids}"
        )

        # stem_anchor.corrected_line_ids 必须同步（在 annotation.corrected_anchors 中）
        stem_anchors = [
            a for a in result.corrected_anchors
            if a.field == "stem" and a.question_number == "1"
        ]
        assert len(stem_anchors) == 1, f"应有 1 个 stem anchor，实际 {len(stem_anchors)}"
        assert stem_anchors[0].corrected_line_ids == ["P1L001", "P1L002"], (
            f"stem_anchor.corrected_line_ids 应同步截断，实际 {stem_anchors[0].corrected_line_ids}。"
            "下游 content_slicer/pipeline/配图仍会用到这个字段。"
        )

    def test_correct_anchors_no_truncation_anchor_unchanged(self):
        """不需要截断时 stem_anchor.corrected_line_ids 保持原值。"""
        from app.domains.document.anchor_corrector import correct_anchors
        from app.domains.document.schemas_l2 import (
            L2DocumentAnnotation,
            L2QuestionAnnotation,
        )

        lines = [
            _line("P1L001", "1. Q1 stem", 1),
            _line("P1L002", "Q1 continuation", 2),
            _line("P1L003", "2. Q2 stem", 3),
        ]
        doc = _doc(lines)

        q1 = L2QuestionAnnotation(
            question_number="1",
            question_type="single_choice",
            stem_line_ids=["P1L001", "P1L002"],
            options_line_ids={"A": ["P1L003"]},
            answer_line_ids=[],
            explanation_line_ids=[],
            is_composite=False,
        )
        annotation = L2DocumentAnnotation(
            filename="test.pdf",
            questions=[q1],
        )

        result = correct_anchors(annotation, doc)

        # 不需要截断
        assert result.questions[0].stem_line_ids == ["P1L001", "P1L002"]
        stem_anchors = [
            a for a in result.corrected_anchors
            if a.field == "stem" and a.question_number == "1"
        ]
        assert len(stem_anchors) == 1
        assert stem_anchors[0].corrected_line_ids == ["P1L001", "P1L002"]

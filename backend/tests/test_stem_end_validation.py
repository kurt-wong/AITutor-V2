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

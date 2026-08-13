"""Tests for L1 dual-source arbiter and merge logic."""

import json
import pytest

from app.domains.document.pipeline import _bbox_iou, _merge_dual_source
from app.domains.document.l1_arbiter import arbitrate_lines, apply_arbitration, L1LineAudit, _contains_body_text, _coverage_check
from app.domains.document.schemas_l1 import L1Document, L1Line, L1Page


class TestBboxIou:
    """测试 bbox IoU 计算。"""

    def test_identical_boxes(self):
        box = {"x1": 0, "y1": 0, "x2": 100, "y2": 50}
        assert _bbox_iou(box, box) == pytest.approx(1.0)

    def test_no_overlap(self):
        box_a = {"x1": 0, "y1": 0, "x2": 10, "y2": 10}
        box_b = {"x1": 20, "y1": 20, "x2": 30, "y2": 30}
        assert _bbox_iou(box_a, box_b) == 0.0

    def test_partial_overlap(self):
        box_a = {"x1": 0, "y1": 0, "x2": 10, "y2": 10}
        box_b = {"x1": 5, "y1": 5, "x2": 15, "y2": 15}
        iou = _bbox_iou(box_a, box_b)
        assert iou == pytest.approx(25 / 175)

    def test_none_bbox(self):
        box = {"x1": 0, "y1": 0, "x2": 10, "y2": 10}
        assert _bbox_iou(None, box) == 0.0
        assert _bbox_iou(box, None) == 0.0
        assert _bbox_iou(None, None) == 0.0


class TestMergeDualSource:
    """测试双源 L1 合并。"""

    def _make_line(self, line_id, text, page_no=1, order=1, bbox=None, block_type="text"):
        return L1Line(
            line_id=line_id, page_no=page_no, line_no_in_page=1, order=order,
            text=text, block_type=block_type, bbox=bbox, source="native",
        )

    def test_merge_with_matching_bbox(self):
        """Lines with matching bbox should produce dual raw_sources."""
        native = L1Document(
            filename="test.pdf",
            pages=[L1Page(page_no=1, lines=[], images=[])],
            lines=[
                self._make_line("N1", "native text", bbox={"x1": 0, "y1": 0, "x2": 100, "y2": 20}),
            ],
            source="native", total_pages=1, text_coverage=1.0,
        )
        pp = L1Document(
            filename="test.pdf",
            pages=[L1Page(page_no=1, lines=[], images=[])],
            lines=[
                self._make_line("P1", "pp text", bbox={"x1": 1, "y1": 1, "x2": 99, "y2": 19}, block_type="formula"),
            ],
            source="ppsv3", total_pages=1, text_coverage=1.0,
        )
        merged, native_only = _merge_dual_source(native, pp)
        assert len(merged.lines) == 1
        line = merged.lines[0]
        assert "native" in line.raw_sources
        assert "ppsv3" in line.raw_sources
        assert line.source == "ppsv3"  # PP is the base

    def test_merge_without_matching_bbox(self):
        """Lines without matching bbox should have single source.
        Native-only lines are logged but not added (preserve line numbering)."""
        native = L1Document(
            filename="test.pdf",
            pages=[L1Page(page_no=1, lines=[], images=[])],
            lines=[
                self._make_line("N1", "native only", bbox={"x1": 0, "y1": 0, "x2": 100, "y2": 20}),
            ],
            source="native", total_pages=1, text_coverage=1.0,
        )
        pp = L1Document(
            filename="test.pdf",
            pages=[L1Page(page_no=1, lines=[], images=[])],
            lines=[
                self._make_line("P1", "pp only", bbox={"x1": 200, "y1": 200, "x2": 300, "y2": 220}),
            ],
            source="ppsv3", total_pages=1, text_coverage=1.0,
        )
        merged, native_only = _merge_dual_source(native, pp)
        # Native-only 行不添加到 merged（保持 PP 行号体系）
        assert len(merged.lines) == 1
        assert native_only == 1
        line = merged.lines[0]
        assert line.raw_sources == {"ppsv3": "pp only"}

    def test_merge_preserves_pp_line_ids(self):
        """Merged L1 should use PP line IDs (PP is the base)."""
        native = L1Document(
            filename="test.pdf",
            pages=[L1Page(page_no=1, lines=[], images=[])],
            lines=[
                self._make_line("N1", "native", bbox={"x1": 0, "y1": 0, "x2": 100, "y2": 20}),
            ],
            source="native", total_pages=1, text_coverage=1.0,
        )
        pp = L1Document(
            filename="test.pdf",
            pages=[L1Page(page_no=1, lines=[], images=[])],
            lines=[
                self._make_line("P1", "pp text", bbox={"x1": 0, "y1": 0, "x2": 100, "y2": 20}),
            ],
            source="ppsv3", total_pages=1, text_coverage=1.0,
        )
        merged, _ = _merge_dual_source(native, pp)
        # postprocess_l1 renumbers to P1L001 format, but source is ppsv3
        assert merged.lines[0].line_id == "P1L001"
        assert merged.lines[0].source == "ppsv3"

    def test_merge_native_only_log(self, caplog):
        """Native-only lines should be logged and returned in count."""
        native = L1Document(
            filename="test.pdf",
            pages=[L1Page(page_no=1, lines=[], images=[])],
            lines=[
                self._make_line("N1", "native only", bbox={"x1": 0, "y1": 0, "x2": 100, "y2": 20}),
                self._make_line("N2", "native also", bbox={"x1": 0, "y1": 20, "x2": 100, "y2": 40}),
            ],
            source="native", total_pages=1, text_coverage=1.0,
        )
        pp = L1Document(
            filename="test.pdf",
            pages=[L1Page(page_no=1, lines=[], images=[])],
            lines=[
                self._make_line("P1", "pp only", bbox={"x1": 200, "y1": 200, "x2": 300, "y2": 220}),
            ],
            source="ppsv3", total_pages=1, text_coverage=1.0,
        )
        with caplog.at_level("INFO", logger="app.domains.document.pipeline"):
            merged, native_only = _merge_dual_source(native, pp)
        assert native_only == 2
        assert len(merged.lines) == 1
        assert any("2 native-only" in record.message for record in caplog.records)


class MockGateway:
    """Mock LLM gateway for testing arbitration."""

    def __init__(self, response: str):
        self._response = response

    async def complete(self, prompt: str, **kwargs) -> str:
        return self._response


class TestArbitrateLines:
    """测试 LLM 行级仲裁。"""

    def _make_doc(self, lines_data):
        lines = []
        for i, (lid, text, raw_sources) in enumerate(lines_data):
            lines.append(L1Line(
                line_id=lid, page_no=1, line_no_in_page=i+1, order=i+1,
                text=text, block_type="text", source="ppsv3",
                raw_sources=raw_sources,
            ))
        return L1Document(
            filename="test.pdf",
            pages=[L1Page(page_no=1, lines=[], images=[])],
            lines=lines, source="mixed", total_pages=1, text_coverage=1.0,
        )

    @pytest.mark.asyncio
    async def test_arbitrate_single_source_lines(self):
        """Single-source lines should get confidence=1.0 without LLM call."""
        doc = self._make_doc([
            ("P1L001", "hello", {"ppsv3": "hello"}),
        ])
        gateway = MockGateway("{}")
        audits = await arbitrate_lines(doc, gateway)
        assert len(audits) == 1
        assert audits[0].confidence == 1.0
        assert audits[0].evidence == "single source"

    @pytest.mark.asyncio
    async def test_arbitrate_dual_source_with_mock_llm(self):
        """Dual-source lines should trigger LLM arbitration."""
        doc = self._make_doc([
            ("P1L001", "pp text", {"ppsv3": "pp text", "native": "native text"}),
        ])
        mock_response = json.dumps([{
            "line_id": "P1L001", "selected_source": "ppsv3",
            "conflict_type": "equivalent", "conflict": False,
            "evidence": "formula better in PP", "confidence": 0.9,
        }])
        gateway = MockGateway(mock_response)
        audits = await arbitrate_lines(doc, gateway)
        assert len(audits) == 1
        assert audits[0].selected_source == "ppsv3"
        assert audits[0].conflict_type == "equivalent"
        assert audits[0].conflict is False
        assert audits[0].confidence == 0.9

    @pytest.mark.asyncio
    async def test_arbitrate_llm_parse_failure_fallback(self):
        """LLM returning invalid JSON should fallback to ppsv3."""
        doc = self._make_doc([
            ("P1L001", "text", {"ppsv3": "text", "native": "text"}),
        ])
        gateway = MockGateway("not valid json {{{")
        audits = await arbitrate_lines(doc, gateway)
        assert len(audits) == 1
        assert audits[0].selected_source == "ppsv3"
        assert audits[0].confidence == 0.5


class TestApplyArbitration:
    """测试仲裁结果应用。"""

    def test_apply_selects_correct_source(self):
        """apply_arbitration should update line text to selected source."""
        doc = L1Document(
            filename="test.pdf",
            pages=[L1Page(page_no=1, lines=[], images=[])],
            lines=[
                L1Line(
                    line_id="P1L001", page_no=1, line_no_in_page=1, order=1,
                    text="pp text", block_type="text", source="ppsv3",
                    raw_sources={"ppsv3": "pp text", "native": "native text"},
                ),
            ],
            source="mixed", total_pages=1, text_coverage=1.0,
        )
        audits = [L1LineAudit(
            line_id="P1L001", selected_source="native",
            conflict_type="equivalent", conflict=False,
            evidence="native more accurate", confidence=0.8,
        )]
        result = apply_arbitration(doc, audits)
        assert result.lines[0].text == "native text"
        assert result.lines[0].selected_source == "native"
        assert result.lines[0].evidence == "native more accurate"

    def test_apply_no_audit_keeps_original(self):
        """Lines without audit should keep original text."""
        doc = L1Document(
            filename="test.pdf",
            pages=[L1Page(page_no=1, lines=[], images=[])],
            lines=[
                L1Line(
                    line_id="P1L001", page_no=1, line_no_in_page=1, order=1,
                    text="original", block_type="text", source="ppsv3",
                ),
            ],
            source="mixed", total_pages=1, text_coverage=1.0,
        )
        result = apply_arbitration(doc, [])
        assert result.lines[0].text == "original"


class TestContainsBodyText:
    """测试 _contains_body_text 防改写检查。"""

    def test_clean_metadata_passes(self):
        """Pure metadata should pass."""
        result = {
            "line_id": "P1L001", "selected_source": "native",
            "conflict": False, "evidence": "native is better", "confidence": 0.9,
        }
        assert _contains_body_text(result) is False

    def test_forbidden_key_text(self):
        """Body text in 'text' field should be rejected."""
        result = {
            "line_id": "P1L001", "selected_source": "native",
            "text": "（2）下列函数中，在定义域内单调递减且值域为正无穷的是",
        }
        assert _contains_body_text(result) is True

    def test_forbidden_key_content(self):
        """Body text in 'content' field should be rejected."""
        result = {
            "line_id": "P1L001", "selected_source": "native",
            "content": "y=2^{-x} is the correct answer for this function question",
        }
        assert _contains_body_text(result) is True

    def test_evidence_with_body_text_rejected(self):
        """Evidence containing body text should be rejected."""
        result = {
            "line_id": "P1L001", "selected_source": "native",
            "evidence": "The correct answer is C because y=2^{-x} satisfies the monotonicity condition and has range (0,+inf) which matches the question requirement",
        }
        assert _contains_body_text(result) is True

    def test_evidence_with_latex_rejected(self):
        """Evidence containing LaTeX should be rejected."""
        result = {
            "line_id": "P1L001", "selected_source": "native",
            "evidence": "Formula \\frac{1}{x} is better recognized by PP",
        }
        assert _contains_body_text(result) is True

    def test_evidence_with_math_delimiters_rejected(self):
        """Evidence containing $ delimiters should be rejected."""
        result = {
            "line_id": "P1L001", "selected_source": "native",
            "evidence": "The expression $y=2^{-x}$ is clearer in PP",
        }
        assert _contains_body_text(result) is True

    def test_evidence_too_long_rejected(self):
        """Evidence exceeding 200 chars should be rejected (likely contains body text)."""
        result = {
            "line_id": "P1L001", "selected_source": "native",
            "evidence": "x" * 201,
        }
        assert _contains_body_text(result) is True

    def test_short_evidence_allowed(self):
        """Short evidence should be allowed."""
        result = {
            "line_id": "P1L001", "selected_source": "native",
            "evidence": "native is more accurate for this text line",
            "confidence": 0.9,
        }
        assert _contains_body_text(result) is False


class TestCoverageCheck:
    """测试 _coverage_check 覆盖校验。"""

    def test_equivalent_still_checks_coverage(self):
        """equivalent 类型也必须执行覆盖校验，不能直接放行。"""
        pp = "(1)A (2)B (3)C"
        native = "(1)A (2)B"  # 缺少 (3)C
        assert _coverage_check(pp, native, "equivalent") is False

    def test_complementary_still_checks_coverage(self):
        """complementary 类型也必须执行覆盖校验。"""
        pp = "(A) option1 (B) option2 (C) option3"
        native = "(A) option1 (B) option2"  # 缺少 (C)
        assert _coverage_check(pp, native, "complementary") is False

    def test_partial_rejects(self):
        """partial 类型直接拒绝。"""
        assert _coverage_check("text", "partial", "partial") is False

    def test_conflicting_checks_coverage(self):
        """conflicting 类型检查覆盖。"""
        pp = "1. question (A) opt1 (B) opt2"
        native = "1. question (A) opt1"  # 缺少 (B)
        assert _coverage_check(pp, native, "conflicting") is False

    def test_full_coverage_passes(self):
        """完全覆盖 → 通过。"""
        pp = "1. question (A) opt1 (B) opt2"
        native = "1. question (A) opt1 (B) opt2"
        assert _coverage_check(pp, native, "equivalent") is True

    def test_native_extra_content_passes(self):
        """native 有额外内容 → 通过。"""
        pp = "1. question (A) opt1"
        native = "1. question (A) opt1 (B) opt2"
        assert _coverage_check(pp, native, "equivalent") is True

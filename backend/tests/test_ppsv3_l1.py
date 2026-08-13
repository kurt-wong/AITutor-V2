"""Tests for PP-StructureV3 L1 conversion and postprocessing."""

import json
import re
from pathlib import Path

import pytest

from app.domains.document.l1_postprocessor import postprocess_l1
from app.domains.document.ppsv3_l1 import extract_l1_from_ocr
from app.domains.document.schemas_l1 import L1Document, L1Line, L1Page
from app.domains.document.schemas import OcrDocument, OcrPage

FIXTURE = Path(__file__).resolve().parents[2] / "test" / "fixtures" / "l1_snapshot_math_real_ppsv3_postprocessed.json"
FIXTURE_RAW = Path(__file__).resolve().parents[2] / "test" / "fixtures" / "l1_snapshot_math_real_ppsv3.json"


def _load_pp_fixture() -> L1Document:
    """从 PP fixture JSON 构建 L1Document。"""
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    pages = [L1Page(page_no=p["page_no"], lines=[], images=[]) for p in data["pages"]]
    lines = [
        L1Line(
            line_id=l["line_id"], page_no=l["page_no"],
            line_no_in_page=l["line_no_in_page"], order=l["order"],
            text=l["text"], block_type=l["block_type"],
            source="ppsv3", continuation=l.get("continuation", False),
        )
        for l in data["lines"]
    ]
    return L1Document(
        filename=data["filename"], pages=pages, lines=lines,
        source="ppsv3", total_pages=len(pages), text_coverage=1.0,
    )


class TestPpsv3Postprocessing:
    """测试 PP L1 postprocessor 对选项行的拆分。"""

    def test_combined_options_are_split(self):
        """combined option lines like (A)...(B)...(C)...(D) should be split."""
        doc = _load_pp_fixture()
        processed = postprocess_l1(doc)

        # P1L010 原始是 "(A)$y=-x$ (B)$y={\\frac{1}{x}}$ (C）$y=2^{-x}$ (D)$y=\\log_{0.5}x$"
        # postprocess 后应拆为 4 行
        page1_options = [
            l for l in processed.lines
            if l.page_no == 1 and 10 <= l.line_no_in_page <= 15
        ]
        option_labels = []
        for l in page1_options:
            if "(A)" in l.text or "（A）" in l.text:
                option_labels.append("A")
            elif "(B)" in l.text or "（B）" in l.text:
                option_labels.append("B")
            elif "(C" in l.text or "（C）" in l.text:
                option_labels.append("C")
            elif "(D)" in l.text or "（D）" in l.text:
                option_labels.append("D")

        assert "A" in option_labels
        assert "B" in option_labels
        assert "C" in option_labels
        assert "D" in option_labels

    def test_line_ids_are_sequential(self):
        """After postprocessing, line IDs should be sequential within each page."""
        doc = _load_pp_fixture()
        processed = postprocess_l1(doc)

        for page_no in range(1, 6):
            page_lines = [l for l in processed.lines if l.page_no == page_no]
            for i, line in enumerate(page_lines, start=1):
                assert line.line_no_in_page == i, (
                    f"Page {page_no} line {i}: expected line_no_in_page={i}, got {line.line_no_in_page}"
                )
                assert line.line_id == f"P{page_no}L{i:03d}"

    def test_total_lines_increase_after_split(self):
        """Postprocessing should produce more lines than raw PP fixture."""
        # 使用未 postprocess 的原始 fixture 测试行数增加
        data = json.loads(FIXTURE_RAW.read_text(encoding="utf-8"))
        pages = [L1Page(page_no=p["page_no"], lines=[], images=[]) for p in data["pages"]]
        lines = [
            L1Line(
                line_id=l["line_id"], page_no=l["page_no"],
                line_no_in_page=l["line_no_in_page"], order=l["order"],
                text=l["text"], block_type=l["block_type"],
                source="ppsv3", continuation=l.get("continuation", False),
            )
            for l in data["lines"]
        ]
        doc = L1Document(
            filename=data["filename"], pages=pages, lines=lines,
            source="ppsv3", total_pages=len(pages), text_coverage=1.0,
        )
        processed = postprocess_l1(doc)
        assert len(processed.lines) > len(doc.lines)


class TestPpsv3L1Conversion:
    """测试 PP OCR output → L1Document 转换。"""

    def test_extract_l1_from_ocr(self):
        """extract_l1_from_ocr should produce valid L1Document."""
        ocr_doc = OcrDocument(
            filename="test.pdf",
            pages=[OcrPage(page_number=1, markdown="# Test\n1. Q1\nA. 1\nB. 2", source_provider="mock")],
            provider_used="mock",
        )
        doc = extract_l1_from_ocr(ocr_doc, filename="test.pdf")
        assert doc.source == "ppsv3"
        assert len(doc.lines) > 0
        assert doc.total_pages == 1

    def test_postprocessed_fixture_matches_golden_line_ids(self):
        """Postprocessed PP fixture line IDs should match golden line IDs."""
        doc = _load_pp_fixture()
        processed = postprocess_l1(doc)
        valid_ids = {l.line_id for l in processed.lines}

        golden_path = Path(__file__).resolve().parents[2] / "test" / "annotations" / "golden" / "math_real_golden.json"
        golden = json.loads(golden_path.read_text(encoding="utf-8"))

        for q in golden["questions"]:
            for lid in q.get("stem_line_ids", []):
                assert lid in valid_ids, f"Q{q['question_number']} stem line {lid} not in postprocessed L1"
            for opt_label, opt_lids in q.get("options_line_ids", {}).items():
                for lid in opt_lids:
                    assert lid in valid_ids, f"Q{q['question_number']} option {opt_label} line {lid} not in postprocessed L1"

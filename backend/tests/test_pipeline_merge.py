"""
Pipeline dual source merge 测试。

H2: 每个 L1 来源（native / ppsv3）在 pipeline 中只被 postprocess_l1 后处理一次，
_merge_dual_source 不再重复调用。

WP6: _merge_dual_source 禁止产生重复 line_id（双源文本匹配不再按 (page, text) 误导匹配）。
"""

import sys
import asyncio
import collections
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock, PropertyMock
from pathlib import Path

from app.domains.document.schemas_l1 import L1Document, L1Line, L1Page
from app.domains.document.schemas import OcrDocument, OcrPage


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PP_PHYSICS_FIXTURE = PROJECT_ROOT / "test" / "fixtures" / "l1_ppsv3_physics_2026.json"


def _make_simple_doc(source: str = "native") -> L1Document:
    """构造简单 L1 文档用于 merge 测试。"""
    prefix = "N" if source == "native" else "P"
    lines = [
        L1Line(f"{prefix}1L001", 1, 1, 1, "1. 测试题干", "text", source=source),
        L1Line(f"{prefix}1L002", 1, 2, 2, "（A）选项A", "text", source=source),
        L1Line(f"{prefix}1L003", 1, 3, 3, "（B）选项B", "text", source=source),
    ]
    return L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source=source,
        total_pages=1,
    )


class TestMergeDualSourceNoPostprocess:
    """H2: _merge_dual_source 本身不调用 postprocess_l1（白盒确认）。"""

    def test_merge_dual_source_does_not_call_postprocess(self):
        """_merge_dual_source 不触发 postprocess_l1。

        H2 修复后，postprocess_l1 已从 _merge_dual_source 中删除。
        native_doc 和 ppsv3_doc 已在各自的 L1 生成阶段后处理过。
        """
        from app.domains.document.pipeline import _merge_dual_source

        native = _make_simple_doc("native")
        ppsv3 = _make_simple_doc("ppsv3")

        with patch("app.domains.document.l1_postprocessor.postprocess_l1") as mock_pp:
            merged, count = _merge_dual_source(native, ppsv3)
            mock_pp.assert_not_called()


class TestH2IntegrationPostprocessCount:
    """H2 集成测试：走完 L1 生成 + merge 全路径，验证 postprocess_l1 调用次数。

    只 mock I/O 层（fitz、OCR chain），让真实 extract_l1_from_pdf、
    convert_ocr_to_l1、_merge_dual_source 和 postprocess_l1 运行。
    """

    def _make_mock_fitz(self):
        """构造 mock fitz 模块（fitz 在函数内 import，需通过 sys.modules 注入）。"""
        blocks = [
            {
                "type": 0,
                "bbox": [50, 100, 500, 130],
                "lines": [{"spans": [{"text": "1. 测试题干"}]}],
            },
            {
                "type": 0,
                "bbox": [50, 140, 500, 170],
                "lines": [{"spans": [{"text": "（A）选项A"}]}],
            },
            {
                "type": 0,
                "bbox": [50, 180, 500, 210],
                "lines": [{"spans": [{"text": "（B）选项B"}]}],
            },
        ]
        mock_page = MagicMock()
        mock_page.get_text.return_value = {"blocks": blocks}
        mock_page.get_images.return_value = []

        mock_doc = MagicMock()
        mock_doc.page_count = 1
        mock_doc.__getitem__ = MagicMock(return_value=mock_page)
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))

        mock_fitz = MagicMock()
        mock_fitz.open.return_value = mock_doc
        return mock_fitz

    def test_dual_source_postprocess_called_exactly_twice(self):
        """native + ppsv3 双源：postprocess_l1 恰好调用 2 次（每源 1 次），merge 不再调用。

        验证链路：extract_l1_from_pdf → postprocess_l1 (1次)
                  convert_ocr_to_l1  → postprocess_l1 (1次)
                  _merge_dual_source → postprocess_l1 (0次)
        总计恰好 2 次。
        """
        from app.domains.document.native_markdown import extract_l1_from_pdf
        from app.domains.document.ppsv3_l1 import extract_l1_from_ocr
        from app.domains.document.pipeline import _merge_dual_source
        from app.domains.document.l1_postprocessor import postprocess_l1 as real_postprocess

        call_count = 0
        call_sources = []

        def counting_postprocess(doc):
            nonlocal call_count
            call_count += 1
            call_sources.append(doc.source)
            return real_postprocess(doc)

        mock_fitz = self._make_mock_fitz()

        # Mock OCR chain（ppsv3 路径 I/O）— extract 是 async
        mock_ocr_page = OcrPage(
            page_number=1,
            markdown="1. 测试题干\n（A）选项A\n（B）选项B",
            source_provider="ppsv3",
        )
        mock_ocr_doc = OcrDocument(
            filename="test.pdf",
            pages=[mock_ocr_page],
        )
        mock_ocr_chain = MagicMock()
        mock_ocr_chain.extract = AsyncMock(return_value=mock_ocr_doc)

        pdf_path = Path("/tmp/test.pdf")

        # postprocess_l1 在 native_markdown 和 ocr_l1_converter 中都是 module-level import
        # 必须 patch 两个导入位置
        with patch.dict(sys.modules, {"fitz": mock_fitz}), \
             patch("app.domains.document.pipeline.build_ocr_chain", return_value=mock_ocr_chain), \
             patch("app.domains.document.native_markdown.postprocess_l1", side_effect=counting_postprocess), \
             patch("app.domains.document.ocr_l1_converter.postprocess_l1", side_effect=counting_postprocess):

            async def run():
                native_doc = extract_l1_from_pdf(pdf_path, filename="test.pdf")
                ocr_doc_obj = await mock_ocr_chain.extract(pdf_path)
                ppsv3_doc = extract_l1_from_ocr(ocr_doc_obj, filename="test.pdf")

                # L1 生成后、merge 前：postprocess_l1 应已调用 2 次
                count_before_merge = call_count

                merged, dual_count = _merge_dual_source(native_doc, ppsv3_doc)
                return native_doc, ppsv3_doc, merged, count_before_merge

            native_doc, ppsv3_doc, merged, count_before_merge = asyncio.run(run())

        # 核心断言 1：L1 生成阶段 postprocess_l1 恰好调用 2 次
        assert count_before_merge == 2, f"postprocess_l1 called {count_before_merge} times during L1 generation, expected 2"
        assert "native" in call_sources, "native source not postprocessed"
        assert "ppsv3" in call_sources, "ppsv3 source not postprocessed"

        # 核心断言 2：merge 阶段 postprocess_l1 没有额外调用
        assert call_count == count_before_merge, (
            f"postprocess_l1 called {call_count - count_before_merge} extra times during merge, expected 0"
        )

        # 验证 L1 生成产出有效行
        assert len(native_doc.lines) > 0, "native L1 should have lines"
        assert len(ppsv3_doc.lines) > 0, "ppsv3 L1 should have lines"
        assert len(merged.lines) > 0, "merged result should have lines"

    def test_single_native_source_postprocess_called_once(self):
        """仅 native 路径：postprocess_l1 恰好调用 1 次。"""
        from app.domains.document.native_markdown import extract_l1_from_pdf

        call_count = 0

        def counting_postprocess(doc):
            nonlocal call_count
            call_count += 1
            from app.domains.document.l1_postprocessor import postprocess_l1 as real_pp
            return real_pp(doc)

        mock_fitz = self._make_mock_fitz()
        pdf_path = Path("/tmp/test.pdf")

        with patch.dict(sys.modules, {"fitz": mock_fitz}), \
             patch("app.domains.document.native_markdown.postprocess_l1", side_effect=counting_postprocess):
            result = extract_l1_from_pdf(pdf_path, filename="test.pdf")

        assert call_count == 1, f"postprocess_l1 called {call_count} times, expected 1"
        assert len(result.lines) > 0

    def test_single_ppsv3_source_postprocess_called_once(self):
        """仅 ppsv3 路径：postprocess_l1 恰好调用 1 次。"""
        from app.domains.document.ocr_l1_converter import convert_ocr_to_l1

        call_count = 0

        def counting_postprocess(doc):
            nonlocal call_count
            call_count += 1
            from app.domains.document.l1_postprocessor import postprocess_l1 as real_pp
            return real_pp(doc)

        ocr_page = OcrPage(
            page_number=1,
            markdown="1. 测试题干\n（A）选项A\n（B）选项B",
            source_provider="ppsv3",
        )
        ocr_doc = OcrDocument(filename="test.pdf", pages=[ocr_page])

        with patch("app.domains.document.ocr_l1_converter.postprocess_l1", side_effect=counting_postprocess):
            result = convert_ocr_to_l1(ocr_doc, filename="test.pdf")

        assert call_count == 1, f"postprocess_l1 called {call_count} times, expected 1"
        assert len(result.lines) > 0


# ── WP6: 双源行 ID 去重 ──────────────────────────────────


class TestMergeDualSourceNoDuplicateLineIds:
    """WP6: _merge_dual_source 禁止产生重复 line_id。

    物理 PP fixture 含重复 (page, text) 行（如 page 6 两次"图2"），
    文本匹配会把不同 orig 行映射到同一 proc 行，导致 merged doc 出现
    重复 line_id（P6L006 出现两次）。line_id 主键匹配消除该问题。
    """

    def test_merge_no_duplicate_line_ids(self):
        """真实 physics PP fixture 合并后无重复 line_id。"""
        fixture = json.loads(
            PP_PHYSICS_FIXTURE.read_text(encoding="utf-8")
        )
        pp_lines = [
            L1Line(
                line_id=l["line_id"], page_no=l["page_no"],
                line_no_in_page=l["line_no_in_page"], order=l["order"],
                text=l["text"], block_type=l.get("block_type", "text"),
                source="ppsv3", continuation=l.get("continuation", False),
                bbox=l.get("bbox"),
            )
            for l in fixture["lines"]
        ]
        pp_pages = [L1Page(page_no=p, lines=[]) for p in range(1, fixture.get("total_pages", max(l.page_no for l in pp_lines)) + 1)]
        pp_doc = L1Document(
            filename=fixture["filename"], pages=pp_pages, lines=pp_lines,
            source="ppsv3", total_pages=fixture.get("total_pages", len(pp_pages)),
        )
        # native doc 使用 N 前缀；行位置仍按 (page, line_no) 对齐
        native_lines = [
            L1Line(
                line_id=f"N{l.line_id[1:]}", page_no=l.page_no,
                line_no_in_page=l.line_no_in_page, order=l.order,
                text=l.text, block_type=l.block_type,
                source="native", continuation=l.continuation,
                bbox=l.bbox,
            )
            for l in pp_lines
        ]
        native_doc = L1Document(
            filename=fixture["filename"], pages=list(pp_pages), lines=native_lines,
            source="native", total_pages=fixture.get("total_pages", len(pp_pages)),
        )

        from app.domains.document.pipeline import _merge_dual_source
        merged, _ = _merge_dual_source(native_doc, pp_doc)
        merged_ids = [l.line_id for l in merged.lines]
        dup_ids = [k for k, v in collections.Counter(merged_ids).items() if v > 1]
        assert not dup_ids, (
            f"merged doc 有重复 line_id: {dup_ids}，"
            f"原始 PP (page,text) 重复行应由 line_id 主键区分"
        )

    def test_merge_preserves_all_orig_line_ids(self):
        """合并后保留所有 orig PP line_id（无遗漏）。"""
        fixture = json.loads(
            PP_PHYSICS_FIXTURE.read_text(encoding="utf-8")
        )
        pp_lines = [
            L1Line(
                line_id=l["line_id"], page_no=l["page_no"],
                line_no_in_page=l["line_no_in_page"], order=l["order"],
                text=l["text"], block_type=l.get("block_type", "text"),
                source="ppsv3", continuation=l.get("continuation", False),
                bbox=l.get("bbox"),
            )
            for l in fixture["lines"]
        ]
        pp_pages = [L1Page(page_no=p, lines=[]) for p in range(1, fixture.get("total_pages", max(l.page_no for l in pp_lines)) + 1)]
        pp_doc = L1Document(
            filename=fixture["filename"], pages=pp_pages, lines=pp_lines,
            source="ppsv3", total_pages=fixture.get("total_pages", len(pp_pages)),
        )
        native_lines = [
            L1Line(
                line_id=f"N{l.line_id[1:]}", page_no=l.page_no,
                line_no_in_page=l.line_no_in_page, order=l.order,
                text=l.text, block_type=l.block_type,
                source="native", continuation=l.continuation,
                bbox=l.bbox,
            )
            for l in pp_lines
        ]
        native_doc = L1Document(
            filename=fixture["filename"], pages=list(pp_pages), lines=native_lines,
            source="native", total_pages=fixture.get("total_pages", len(pp_pages)),
        )

        from app.domains.document.pipeline import _merge_dual_source
        from app.domains.document.l1_postprocessor import postprocess_l1
        pp_doc = postprocess_l1(pp_doc)
        native_doc = postprocess_l1(native_doc)
        merged, _ = _merge_dual_source(native_doc, pp_doc)

        orig_ids = {l.line_id for l in pp_lines}
        merged_ids = {l.line_id for l in merged.lines}
        # 页脚行（"第x页/共y页"）会被 postprocess_l1 过滤，不参与合并
        import re
        _PAGE_FOOTER_RE = re.compile(r"^\s*第\s*\d+\s*页/共\s*\d+\s*页\s*$")
        footer_ids = {l.line_id for l in pp_lines if _PAGE_FOOTER_RE.match(l.text or "")}
        missing = orig_ids - merged_ids - footer_ids
        assert not missing, f"合并后丢失 orig line_id: {missing}"
        assert all(line.line_id.startswith("P") for line in merged.lines), (
            "canonical merged line_id 必须保留 PP 行号体系"
        )
        native_lids = [
            raw.get("native_line_id")
            for line in merged.lines
            for raw in [line.raw_sources]
            if raw.get("native_line_id")
        ]
        assert native_lids, "merged raw_sources 应保留 native_line_id 溯源"
        assert all(lid.startswith("N") for lid in native_lids), (
            f"native_line_id 必须使用 N 前缀: {native_lids[:10]}"
        )


class TestNativePpLineIdSeparation:
    """Native/PP 行号编码分离：canonical 保留 PP，native 只进 raw_sources。"""

    def test_merge_simple_docs_keeps_pp_canonical(self):
        """简单双源 merge 后 canonical line_id 为 P，native_line_id 为 N。"""
        from app.domains.document.pipeline import _merge_dual_source

        native = _make_simple_doc("native")
        ppsv3 = _make_simple_doc("ppsv3")
        merged, _ = _merge_dual_source(native, ppsv3)

        assert len(merged.lines) == 3
        assert all(line.line_id.startswith("P") for line in merged.lines)
        assert all(
            line.raw_sources.get("native_line_id", "").startswith("N")
            for line in merged.lines
        )
        assert not any(line.line_id.startswith("N") for line in merged.lines)

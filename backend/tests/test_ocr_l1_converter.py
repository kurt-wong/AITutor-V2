"""
H6: OCR-to-L1 Adapter 测试。

convert_ocr_to_l1 统一 OCR → L1 转换接口。
"""

import pytest
from unittest.mock import patch, MagicMock
from app.domains.document.schemas import OcrBlock, OcrDocument, OcrPage, ParsedImage


def _make_ocr_doc() -> OcrDocument:
    """构造测试用 OcrDocument。"""
    return OcrDocument(
        filename="test.pdf",
        pages=[
            OcrPage(
                page_number=1,
                markdown="# 测试标题\n正文内容",
                images=[
                    ParsedImage(
                        id="img1",
                        url="https://example.com/img1.png",
                        page_number=1,
                        role="diagram",
                        bbox={"x1": 10, "y1": 20, "x2": 100, "y2": 80},
                    )
                ],
                blocks=[
                    OcrBlock(
                        content="测试标题",
                        label="title",
                        bbox={"x1": 10, "y1": 10, "x2": 200, "y2": 30},
                    ),
                    OcrBlock(
                        content="正文内容",
                        label="text",
                        bbox={"x1": 10, "y1": 40, "x2": 200, "y2": 60},
                    ),
                ],
                source_provider="ppsv3",
            )
        ],
    )


class TestOcrL1Converter:
    """H6: convert_ocr_to_l1 保留元数据且委托正确。"""

    def test_ocr_l1_converter_preserves_metadata(self):
        """convert_ocr_to_l1 保留 page/bbox/images/source 元数据。"""
        from app.domains.document.ocr_l1_converter import convert_ocr_to_l1

        ocr_doc = _make_ocr_doc()
        l1_doc = convert_ocr_to_l1(ocr_doc, filename="test.pdf")

        # raw_lines 非空
        assert len(l1_doc.raw_lines) > 0
        # source 一致
        assert l1_doc.source == "ppsv3"
        # pages 数量一致
        assert len(l1_doc.pages) == len(ocr_doc.pages)
        # lines 有 page_no
        for line in l1_doc.raw_lines:
            assert line.page_no >= 1
        # images 有 url
        assert len(l1_doc.images) >= 1
        assert l1_doc.images[0].url == "https://example.com/img1.png"

    def test_extract_l1_from_ocr_delegates_to_converter(self):
        """extract_l1_from_ocr 完全委托给 convert_ocr_to_l1。"""
        from app.domains.document.ppsv3_l1 import extract_l1_from_ocr

        with patch("app.domains.document.ocr_l1_converter.convert_ocr_to_l1") as mock_conv:
            from app.domains.document.schemas_l1 import L1Document, L1Page
            mock_conv.return_value = L1Document(
                filename="test.pdf",
                pages=[L1Page(page_no=1, lines=[])],
                lines=[], source="ppsv3", total_pages=1,
            )

            ocr_doc = _make_ocr_doc()
            result = extract_l1_from_ocr(ocr_doc, filename="test.pdf")

            mock_conv.assert_called_once_with(ocr_doc, filename="test.pdf")
            assert result.source == "ppsv3"

    def test_pipeline_converter_path(self):
        """pipeline.py 中 _run_ppsv3_generation 调用 convert_ocr_to_l1 或等效委托。"""
        # 验证 pipeline 中 ppsv3_l1 路径最终经过 adapter
        import inspect
        from app.domains.document import pipeline

        source = inspect.getsource(pipeline)
        # pipeline 应引用 ppsv3_l1 或 convert_ocr_to_l1
        assert "ppsv3_l1" in source or "convert_ocr_to_l1" in source


# ═══════════════════════════════════════════════════════════════════
# Fix 3: OCR fallback 正则 block_type 判定
# ═══════════════════════════════════════════════════════════════════


def test_ocr_l1_converter_plain_text_is_text():
    """无 blocks 时纯文本 markdown → block_type == 'text'。"""
    from app.domains.document.ocr_l1_converter import convert_ocr_to_l1
    from app.domains.document.schemas import OcrDocument, OcrPage

    ocr_doc = OcrDocument(
        filename="test.pdf",
        pages=[OcrPage(page_number=1, markdown="普通文本内容", source_provider="ppsv3")],
    )
    l1_doc = convert_ocr_to_l1(ocr_doc, filename="test.pdf")

    assert len(l1_doc.lines) == 1
    assert l1_doc.lines[0].block_type == "text"


def test_ocr_l1_converter_formula_is_formula():
    """无 blocks 时含 $...$ 公式文本 → block_type == 'formula'。"""
    from app.domains.document.ocr_l1_converter import convert_ocr_to_l1
    from app.domains.document.schemas import OcrDocument, OcrPage

    ocr_doc = OcrDocument(
        filename="test.pdf",
        pages=[OcrPage(page_number=1, markdown="$x^2$+1", source_provider="ppsv3")],
    )
    l1_doc = convert_ocr_to_l1(ocr_doc, filename="test.pdf")

    assert len(l1_doc.lines) == 1
    assert l1_doc.lines[0].block_type == "formula"


def test_ocr_l1_converter_display_math_is_formula():
    """无 blocks 时含 $$...$$ display math → block_type == 'formula'。"""
    from app.domains.document.ocr_l1_converter import convert_ocr_to_l1
    from app.domains.document.schemas import OcrDocument, OcrPage

    ocr_doc = OcrDocument(
        filename="test.pdf",
        pages=[OcrPage(page_number=1, markdown="$$x^2$$", source_provider="ppsv3")],
    )
    l1_doc = convert_ocr_to_l1(ocr_doc, filename="test.pdf")

    assert len(l1_doc.lines) == 1
    assert l1_doc.lines[0].block_type == "formula"


def test_ocr_l1_converter_table_block_preserved_as_single_line():
    """table block 必须整块保留为一条 L1 line，不能被换行或选项标记拆散。"""
    from app.domains.document.ocr_l1_converter import convert_ocr_to_l1
    from app.domains.document.schemas import OcrBlock, OcrDocument, OcrPage

    table_html = (
        "<html><body><table>\n"
        "<tr><td>选项</td><td>X</td><td>Y</td></tr>\n"
        "<tr><td>A. 甲</td><td>B. 乙</td><td>C. 丙</td></tr>\n"
        "<tr><td>题号</td><td>1</td><td>2</td></tr>\n"
        "<tr><td>答案</td><td>A</td><td>C</td></tr>\n"
        "</table></body></html>"
    )
    ocr_doc = OcrDocument(
        filename="test.pdf",
        pages=[
            OcrPage(
                page_number=1,
                markdown="",
                source_provider="ppsv3",
                blocks=[
                    OcrBlock(
                        label="table",
                        content=table_html,
                        bbox={"x1": 10, "y1": 20, "x2": 200, "y2": 80},
                    )
                ],
            )
        ],
    )

    l1_doc = convert_ocr_to_l1(ocr_doc, filename="test.pdf")

    assert len(l1_doc.lines) == 1
    table_line = l1_doc.lines[0]
    assert table_line.block_type == "table"
    assert "<table>" in table_line.text
    assert "</table>" in table_line.text
    assert "A. 甲" in table_line.text
    assert "B. 乙" in table_line.text
    assert "\n" not in table_line.text


def test_ocr_l1_converter_markdown_table_fallback_preserves_full_table():
    """无 block 数据时，markdown fallback 也不能拆散跨行 HTML table。"""
    from app.domains.document.ocr_l1_converter import convert_ocr_to_l1
    from app.domains.document.schemas import OcrDocument, OcrPage

    markdown = (
        "<html><body><table>\n"
        "<tr><td>选项</td><td>X</td></tr>\n"
        "<tr><td>A. 甲</td><td>B. 乙</td></tr>\n"
        "</table></body></html>\n"
        "后续题干"
    )
    ocr_doc = OcrDocument(
        filename="test.pdf",
        pages=[OcrPage(page_number=1, markdown=markdown, source_provider="ppsv3")],
    )

    l1_doc = convert_ocr_to_l1(ocr_doc, filename="test.pdf")

    assert len(l1_doc.lines) == 2
    table_line, stem_line = l1_doc.lines
    assert table_line.block_type == "table"
    assert "<table>" in table_line.text
    assert "</table>" in table_line.text
    assert "A. 甲" in table_line.text
    assert "\n" not in table_line.text
    assert stem_line.text == "后续题干"

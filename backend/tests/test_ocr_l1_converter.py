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


def test_ocr_l1_converter_answer_table_stays_single_line():
    """答案表（题号/答案 两行单字母）保持单行，不被拆散。

    2026-08-26（LOG v6.37）：只有"选项表"（选项标签在表格内部）拆行；
    答案表首列是"题号/答案"字样、单元格是单字母数据 → 保持单行，
    保证 answer_matcher 的 _parse_html_answer_table 能找到完整 <table>。
    """
    from app.domains.document.ocr_l1_converter import convert_ocr_to_l1
    from app.domains.document.schemas import OcrBlock, OcrDocument, OcrPage

    table_html = (
        "<html><body><table>\n"
        "<tr><td>题号</td><td>1</td><td>2</td><td>3</td></tr>\n"
        "<tr><td>答案</td><td>A</td><td>C</td><td>B</td></tr>\n"
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
    assert "题号" in table_line.text
    assert "答案" in table_line.text
    assert "\n" not in table_line.text


def test_ocr_l1_converter_markdown_table_fallback_keeps_answer_table():
    """无 block 数据时，markdown fallback 对答案表保持单行（不拆散跨行 table）。"""
    from app.domains.document.ocr_l1_converter import convert_ocr_to_l1
    from app.domains.document.schemas import OcrDocument, OcrPage

    markdown = (
        "<html><body><table>\n"
        "<tr><td>题号</td><td>1</td><td>2</td></tr>\n"
        "<tr><td>答案</td><td>A</td><td>C</td></tr>\n"
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
    assert "题号" in table_line.text
    assert "\n" not in table_line.text
    assert stem_line.text == "后续题干"


def test_ocr_l1_converter_option_table_split_into_lines():
    """选项表（选项标签在表格内部，首列 <td>A</td>）拆成独立 L1 行。

    2026-08-26（LOG v6.37）：化学表格选项题（如"读表完成实验判断"），
    VL OCR 把整表识别为单行 → LLM 无法给选项独立行号 → 锚点校验失败。
    拆行后每选项一行（`A. <内容>` 格式），LLM 可锚定。
    """
    from app.domains.document.ocr_l1_converter import convert_ocr_to_l1
    from app.domains.document.schemas import OcrBlock, OcrDocument, OcrPage

    table_html = (
        "<html><body><table>"
        "<tr><td></td><td>事实</td><td>推测</td></tr>"
        "<tr><td>A</td><td>NaCl 固体与浓硫酸反应可制备 HCl 气体</td><td>NaI 固体与浓硫酸反应可制备 HI 气体</td></tr>"
        "<tr><td>B</td><td>HI 在 230℃时分解</td><td>HF 分解温度大于 1500℃</td></tr>"
        "<tr><td>C</td><td>H3PO4 是中强酸</td><td>HClO4 是强酸</td></tr>"
        "<tr><td>D</td><td>Na、Al 通常用电解法冶炼</td><td>Mg 可用电解法冶炼</td></tr>"
        "</table></body></html>"
    )
    ocr_doc = OcrDocument(
        filename="test.pdf",
        pages=[
            OcrPage(
                page_number=1,
                markdown="",
                source_provider="ppsv3",
                blocks=[OcrBlock(label="table", content=table_html, bbox={})],
            )
        ],
    )

    l1_doc = convert_ocr_to_l1(ocr_doc, filename="test.pdf")
    lines = l1_doc.lines
    # 表头行 + 4 个选项行
    assert len(lines) == 5, [l.text for l in lines]
    assert lines[0].block_type == "table"
    assert lines[0].text == "事实，推测"  # 表头行（首列空单元格被过滤）
    assert lines[1].text == "A. NaCl 固体与浓硫酸反应可制备 HCl 气体，NaI 固体与浓硫酸反应可制备 HI 气体"
    assert lines[2].text.startswith("B. ")
    assert lines[3].text.startswith("C. ")
    assert lines[4].text.startswith("D. ")


def test_ocr_l1_converter_2x2_img_table_split():
    """2×2 表格（选项文字 + 装置图单元格）拆行，图片引用保留在选项行。

    八十中 Q10：第一行 <td>A. 制备 Fe(OH)3 胶体</td>...，第二行 <td><img.../></td>。
    拆行后选项行含图片引用，锚点校验可识别 A./B./C./D.。
    """
    from app.domains.document.ocr_l1_converter import convert_ocr_to_l1
    from app.domains.document.schemas import OcrBlock, OcrDocument, OcrPage

    table_html = (
        "<table>"
        "<tr><td>A. 制备 $ \\ce{Fe(OH)3} $ 胶体</td><td>B. 实验室制备 $ \\ce{CO2} $</td>"
        "<td>C. 向容量瓶中转移溶液</td><td>D. 验证 $ \\ce{H2} $ 可以在 $ \\ce{Cl2} $ 中燃烧</td></tr>"
        "<tr><td><img src=\"imgs/img1.jpg\"/></td><td><img src=\"imgs/img2.jpg\"/></td>"
        "<td><img src=\"imgs/img3.jpg\"/></td><td><img src=\"imgs/img4.jpg\"/></td></tr>"
        "</table>"
    )
    ocr_doc = OcrDocument(
        filename="test.pdf",
        pages=[
            OcrPage(
                page_number=1,
                markdown="",
                source_provider="ppsv3",
                blocks=[OcrBlock(label="table", content=table_html, bbox={})],
            )
        ],
    )

    l1_doc = convert_ocr_to_l1(ocr_doc, filename="test.pdf")
    lines = l1_doc.lines
    # 第一行选项文本在 <td> 里（A. 开头）→ 拆成 4 个选项行；
    # 第二行是纯图片单元格（无选项标签）→ 保留为 1 行
    assert len(lines) == 5, [l.text for l in lines]
    assert lines[0].text == "A. 制备 $ \\ce{Fe(OH)3} $ 胶体"
    assert lines[1].text == "B. 实验室制备 $ \\ce{CO2} $"
    assert lines[2].text == "C. 向容量瓶中转移溶液"
    assert lines[3].text == "D. 验证 $ \\ce{H2} $ 可以在 $ \\ce{Cl2} $ 中燃烧"
    assert "<img" in lines[4].text


def test_ocr_l1_converter_data_table_stays_single_line():
    """资料表（选项在表外普通行，表格只是题干资料）保持单行。

    北师大二附 Q13：表格是反应数据（首列 ①② 非 A-G 标签），
    选项 A/B/C/D 在表格外的普通行 → 不拆行。
    """
    from app.domains.document.ocr_l1_converter import convert_ocr_to_l1
    from app.domains.document.schemas import OcrBlock, OcrDocument, OcrPage

    table_html = (
        "<table>"
        "<tr><td rowspan=\"2\">反应序号</td><td rowspan=\"2\">起始酸碱性</td>"
        "<td>KI</td><td>$ KMnO_{4} $</td><td rowspan=\"2\">还原产物</td><td rowspan=\"2\">氧化产物</td></tr>"
        "<tr><td>物质的量/mol</td><td>物质的量/mol</td></tr>"
        "<tr><td>①</td><td>酸性</td><td>0.001</td><td>n</td><td>$ Mn^{2+} $</td><td>$ I_{2} $</td></tr>"
        "</table>"
    )
    ocr_doc = OcrDocument(
        filename="test.pdf",
        pages=[
            OcrPage(
                page_number=1,
                markdown="",
                source_provider="ppsv3",
                blocks=[OcrBlock(label="table", content=table_html, bbox={})],
            )
        ],
    )

    l1_doc = convert_ocr_to_l1(ocr_doc, filename="test.pdf")
    # 首列无 A-G 纯标签 → 不拆行，保持单行
    assert len(l1_doc.lines) == 1
    assert "<table>" in l1_doc.lines[0].text
    assert "</table>" in l1_doc.lines[0].text

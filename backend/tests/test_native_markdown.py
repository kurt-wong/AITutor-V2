"""Native PDF L1 生成器单元测试。"""

from pathlib import Path

from app.domains.document.native_markdown import extract_l1_from_pdf

TEST_PDF = (
    Path(__file__).resolve().parents[2]
    / "test"
    / "pdf"
    / "2026北京朝阳高一（上）期末数学（教师版）.pdf"
)


def test_extract_l1_returns_document():
    """提取 L1 返回完整的 L1Document。"""
    result = extract_l1_from_pdf(TEST_PDF, page_range=(1, 1))
    assert result.filename == TEST_PDF.name
    assert result.source == "native"
    assert result.total_pages == 1
    assert len(result.lines) > 0
    assert len(result.pages) == 1


def test_line_ids_are_continuous():
    """行号连续不跳号。"""
    result = extract_l1_from_pdf(TEST_PDF, page_range=(1, 2))
    orders = [l.order for l in result.lines]
    assert orders == list(range(1, len(orders) + 1))
    for page in result.pages:
        page_line_orders = [l.line_no_in_page for l in page.lines]
        assert page_line_orders == list(range(1, len(page_line_orders) + 1))


def test_line_id_format():
    """Native 行 ID 格式为 N{page}L{line:03d}。"""
    result = extract_l1_from_pdf(TEST_PDF, page_range=(1, 1))
    for line in result.lines:
        assert line.line_id.startswith("N1L")
        assert len(line.line_id) == 6


def test_text_coverage_positive():
    """文本层覆盖率为正数。"""
    result = extract_l1_from_pdf(TEST_PDF, page_range=(1, 1))
    assert result.text_coverage > 0


def test_postprocessing_applied():
    """后处理已应用（选项被拆分）。"""
    result = extract_l1_from_pdf(TEST_PDF, page_range=(1, 1))
    option_lines = [
        l for l in result.lines
        if "（A）" in l.text or "（B）" in l.text
    ]
    for line in option_lines:
        count_a = line.text.count("（A）")
        count_b = line.text.count("（B）")
        assert count_a + count_b <= 1


def test_raw_lines_preserved():
    """raw_lines 保留处理前的原始行。"""
    result = extract_l1_from_pdf(TEST_PDF, page_range=(1, 1))
    assert len(result.raw_lines) > 0


def test_page_range_respected():
    """页码范围被正确处理。"""
    result_1page = extract_l1_from_pdf(TEST_PDF, page_range=(1, 1))
    result_2pages = extract_l1_from_pdf(TEST_PDF, page_range=(1, 2))
    assert len(result_1page.lines) < len(result_2pages.lines)
    assert result_1page.total_pages == 1
    assert result_2pages.total_pages == 2

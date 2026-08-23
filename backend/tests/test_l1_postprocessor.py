"""L1 后处理器单元测试。"""

from app.domains.document.schemas_l1 import L1Document, L1Line, L1Page
from app.domains.document.l1_postprocessor import postprocess_l1


def _make_doc(lines: list[str], page_no: int = 1) -> L1Document:
    """辅助函数：从文本列表构造 L1Document。"""
    l1_lines = []
    for i, text in enumerate(lines, start=1):
        l1_lines.append(
            L1Line(
                line_id=f"P{page_no}L{i:03d}",
                page_no=page_no,
                line_no_in_page=i,
                order=i,
                text=text,
                block_type="text",
            )
        )
    return L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=page_no, lines=l1_lines)],
        lines=l1_lines,
        total_pages=1,
    )


def test_no_split_needed():
    """正常行不需要拆分。"""
    doc = _make_doc([
        "1. 下列函数中，最小正周期为π的是",
        "A. y = sin x",
        "B. y = cos x",
    ])
    result = postprocess_l1(doc)
    assert len(result.lines) == 3
    assert result.lines[0].text == "1. 下列函数中，最小正周期为π的是"
    assert result.lines[0].line_id == "P1L001"


def test_inline_question_number_split():
    """题号与上一题选项挤在同一行时拆分。"""
    doc = _make_doc([
        "D. 既不充分也不必要条件5.已知函数f(x)=x²-2x+1",
    ])
    result = postprocess_l1(doc)
    assert len(result.lines) == 2
    assert "D." in result.lines[0].text
    assert "5." in result.lines[1].text


def test_inline_paren_question_number_split():
    """行内括号题号（16）前必须强制换行。"""
    doc = _make_doc([
        "②为保证会员充值优惠成立，则k的最大值为（16）关于定义域为R的函数",
    ])
    result = postprocess_l1(doc)
    assert len(result.lines) == 2
    assert result.lines[1].text.startswith("（16）")


def test_parenthesized_number_in_formula_not_split():
    """公式中的 (1) 不应被当成题号拆分。"""
    doc = _make_doc([
        "若 $f(x)=(1)$，则结论成立",
    ])
    result = postprocess_l1(doc)
    assert len(result.lines) == 1
    assert "(1)" in result.lines[0].text


def test_decimal_no_split():
    """小数不应被误拆。"""
    doc = _make_doc([
        "3.2x + 5 = 15 的解为 x = 3.125",
    ])
    result = postprocess_l1(doc)
    assert len(result.lines) == 1
    assert "3.2x" in result.lines[0].text


def test_table_line_skips_question_and_option_split():
    """table block 不参与题号/选项行内拆分。"""
    line = L1Line(
        line_id="P1L001",
        page_no=1,
        line_no_in_page=1,
        order=1,
        text=(
            "<table><tr><td>1. 材料</td><td>A. 甲</td>"
            "<td>B. 乙</td></tr></table>"
        ),
        block_type="table",
    )
    doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=[line])],
        lines=[line],
        total_pages=1,
    )

    result = postprocess_l1(doc)

    assert len(result.lines) == 1
    assert result.lines[0].block_type == "table"
    assert "<table>" in result.lines[0].text
    assert "A. 甲" in result.lines[0].text


def test_inline_options_split():
    """单行多选项切分为多行。"""
    doc = _make_doc([
        "A.充分不必要条件B.必要不充分条件C.充要条件D.既不充分也不必要条件",
    ])
    result = postprocess_l1(doc)
    assert len(result.lines) == 4
    assert result.lines[0].text.startswith("A.")
    assert result.lines[1].text.startswith("B.")
    assert result.lines[2].text.startswith("C.")
    assert result.lines[3].text.startswith("D.")


def test_renumber连续():
    """拆分后行号连续不跳号。"""
    doc = _make_doc([
        "1. 第一题",
        "D.选项D5.第二题",
        "A.x=1B.x=2C.x=3D.x=4",
    ])
    result = postprocess_l1(doc)
    orders = [l.order for l in result.lines]
    assert orders == list(range(1, len(orders) + 1))
    for i, line in enumerate(result.lines, start=1):
        assert line.line_id == f"P1L{i:03d}"


def test_multi_page_renumber():
    """跨页时行号按页分组重编。"""
    lines = [
        L1Line("P1L001", 1, 1, 1, "1. 题目一", "text"),
        L1Line("P1L002", 1, 2, 2, "A.选项A", "text"),
        L1Line("P2L001", 2, 1, 3, "2. 题目二", "text"),
        L1Line("P2L002", 2, 2, 4, "B.选项B", "text"),
    ]
    doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(1), L1Page(2)],
        lines=lines,
        total_pages=2,
    )
    result = postprocess_l1(doc)
    assert result.lines[0].line_id == "P1L001"
    assert result.lines[1].line_id == "P1L002"
    assert result.lines[2].line_id == "P2L001"
    assert result.lines[3].line_id == "P2L002"


def test_preserves_block_type():
    """拆分后保持原始 block_type。"""
    doc = _make_doc([
        "D.选项5.新题",
    ])
    result = postprocess_l1(doc)
    assert all(l.block_type == "text" for l in result.lines)


def test_empty_line_skipped():
    """拆分后空行被跳过。"""
    doc = _make_doc([
        "1.题目",
    ])
    result = postprocess_l1(doc)
    assert len(result.lines) == 1
    assert result.lines[0].text == "1.题目"


def test_raw_lines_preserved():
    """raw_lines 保留处理前的原始行。"""
    doc = _make_doc([
        "1.题目A.x=1B.x=2",
    ])
    result = postprocess_l1(doc)
    # 原始文档只有1行
    assert len(doc.lines) == 1
    # raw_lines 保留原始1行
    assert len(result.raw_lines) == 1
    # canonical lines 被拆分
    assert len(result.lines) == 3  # "1.题目" + "A.x=1" + "B.x=2"


def test_pages_synced_with_canonical_lines():
    """pages[].lines 同步为 canonical lines。"""
    doc = _make_doc([
        "1.题目A.x=1B.x=2",
    ])
    result = postprocess_l1(doc)
    # pages 的行应该与 canonical lines 一致
    assert len(result.pages[0].lines) == len(result.lines)
    # 每个 page line 的 line_id 应该与 canonical line 一致
    for i, (page_line, canonical_line) in enumerate(
        zip(result.pages[0].lines, result.lines)
    ):
        assert page_line.line_id == canonical_line.line_id


def test_original_document_not_modified():
    """原始文档不被修改。"""
    doc = _make_doc([
        "1.题目A.x=1B.x=2",
    ])
    original_lines_count = len(doc.lines)
    original_first_line_text = doc.lines[0].text
    result = postprocess_l1(doc)
    # 原始文档不变
    assert len(doc.lines) == original_lines_count
    assert doc.lines[0].text == original_first_line_text
    assert len(doc.raw_lines) == 0  # 原始文档没有 raw_lines


def test_digit_dot_not_split():
    """数字内点号不被误拆为题号（如 2015. 中的 5.）。"""
    doc = _make_doc([
        "4. She has been working as a teacher ______ 2015.",
    ])
    result = postprocess_l1(doc)
    # 2015. 不应被拆分，应保持为 1 行
    assert len(result.lines) == 1
    assert "2015." in result.lines[0].text


def test_paren_options_split():
    """括号选项格式 （A）xxx（B）xxx 切分为多行。"""
    doc = _make_doc([
        "（A）y = x⁻¹            （B）y = 1/x           （C）y = 2⁻ˣ        （D）y = log₀.₅x",
    ])
    result = postprocess_l1(doc)
    assert len(result.lines) == 4
    assert "（A）" in result.lines[0].text
    assert "（B）" in result.lines[1].text
    assert "（C）" in result.lines[2].text
    assert "（D）" in result.lines[3].text


def test_mixed_options_format():
    """混合格式：A. 和 （A） 同行时都能拆分。"""
    doc = _make_doc([
        "A.选项一（B）选项二C.选项三（D）选项四",
    ])
    result = postprocess_l1(doc)
    assert len(result.lines) == 4
    assert result.lines[0].text.startswith("A.")
    assert "（B）" in result.lines[1].text
    assert result.lines[2].text.startswith("C.")
    assert "（D）" in result.lines[3].text


def test_native_source_uses_n_line_id_prefix():
    """Native L1 无旧 P 前缀输入时，postprocess 使用 N 行号。"""
    line = L1Line(
        line_id="", page_no=1, line_no_in_page=1, order=1,
        text="1. 测试题干", block_type="text", source="native",
    )
    doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=[line])],
        lines=[line],
        source="native",
        total_pages=1,
    )
    result = postprocess_l1(doc)
    assert result.lines[0].line_id == "N1L001"


def test_ppsv3_source_uses_p_line_id_prefix():
    """PP L1 无旧行号输入时，postprocess 使用 P 行号。"""
    line = L1Line(
        line_id="", page_no=1, line_no_in_page=1, order=1,
        text="1. 测试题干", block_type="text", source="ppsv3",
    )
    doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=[line])],
        lines=[line],
        source="ppsv3",
        total_pages=1,
    )
    result = postprocess_l1(doc)
    assert result.lines[0].line_id == "P1L001"

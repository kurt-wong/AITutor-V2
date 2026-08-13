"""内容切片器单元测试。"""

from app.domains.document.content_slicer import slice_questions
from app.domains.document.schemas_l1 import L1Document, L1Line, L1Page
from app.domains.document.schemas_l2 import L2DocumentAnnotation, L2QuestionAnnotation


def _make_doc() -> L1Document:
    """构造测试 L1 文档。"""
    lines = [
        L1Line("P1L001", 1, 1, 1, "1. 已知函数f(x)=2x+1，则f(3)=", "text"),
        L1Line("P1L002", 1, 2, 2, "（A）5", "text"),
        L1Line("P1L003", 1, 3, 3, "（B）6", "text"),
        L1Line("P1L004", 1, 4, 4, "（C）7", "text"),
        L1Line("P1L005", 1, 5, 5, "（D）8", "text"),
        L1Line("P1L006", 1, 6, 6, "2. 计算：√4 + √9 =", "text"),
        L1Line("P1L007", 1, 7, 7, "（A）3", "text"),
        L1Line("P1L008", 1, 8, 8, "（B）4", "text"),
        L1Line("P1L009", 1, 9, 9, "（C）5", "text"),
        L1Line("P1L010", 1, 10, 10, "（D）6", "text"),
    ]
    return L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source="native",
        total_pages=1,
    )


def test_slice_stem():
    """切片题干文本。"""
    doc = _make_doc()
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="1",
                question_type="single_choice",
                stem_line_ids=["P1L001"],
                options_line_ids={},
            )
        ],
    )

    result = slice_questions(annotation, doc)
    assert len(result) == 1
    assert "已知函数f(x)=2x+1" in result[0].stem


def test_slice_options_strips_label():
    """切片选项时去掉选项标签前缀。"""
    doc = _make_doc()
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="1",
                question_type="single_choice",
                stem_line_ids=["P1L001"],
                options_line_ids={
                    "A": ["P1L002"],
                    "B": ["P1L003"],
                    "C": ["P1L004"],
                    "D": ["P1L005"],
                },
            )
        ],
    )

    result = slice_questions(annotation, doc)
    opts = {o["label"]: o["text"] for o in result[0].options}
    assert opts["A"] == "5"
    assert opts["B"] == "6"
    assert opts["C"] == "7"
    assert opts["D"] == "8"


def test_slice_multi_line_stem():
    """切片多行题干。"""
    doc = _make_doc()
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="1",
                question_type="single_choice",
                stem_line_ids=["P1L001", "P1L002"],
                options_line_ids={},
            )
        ],
    )

    result = slice_questions(annotation, doc)
    assert "\n" in result[0].stem


def test_slice_empty_line_ids():
    """空行 ID 切片为空文本。"""
    doc = _make_doc()
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="1",
                question_type="single_choice",
                stem_line_ids=[],
                options_line_ids={},
            )
        ],
    )

    result = slice_questions(annotation, doc)
    assert result[0].stem == ""
    assert result[0].options == []


def test_slice_preserves_metadata():
    """切片保留题目元数据。"""
    doc = _make_doc()
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="1",
                question_type="single_choice",
                stem_line_ids=["P1L001"],
                options_line_ids={"A": ["P1L002"]},
                difficulty=2,
                score=5.0,
                knowledge_points=["函数"],
                source_page=1,
            )
        ],
    )

    result = slice_questions(annotation, doc)
    assert result[0].difficulty == 2
    assert result[0].score == 5.0
    assert result[0].knowledge_points == ["函数"]
    assert result[0].source_page == 1


def test_slice_canonicalizes_chinese_question_type():
    """中文题型归一化为 canonical 枚举。"""
    doc = _make_doc()
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="1",
                question_type="填空题",
                stem_line_ids=["P1L001"],
                options_line_ids={},
            )
        ],
    )

    result = slice_questions(annotation, doc)
    assert result[0].question_type == "fill_in"

"""答案与详解匹配器单元测试。"""

from app.domains.document.answer_matcher import match_answers
from app.domains.document.schemas_l1 import L1Document, L1Line, L1Page
from app.domains.document.schemas_l2 import SlicedQuestion


def _make_doc_with_answer_table() -> L1Document:
    """构造包含答案表的 L1 文档。"""
    lines = [
        L1Line("P1L001", 1, 1, 1, "1. 已知函数f(x)=2x+1，则f(3)=", "text"),
        L1Line("P1L002", 1, 2, 2, "（A）5", "text"),
        L1Line("P1L003", 1, 3, 3, "（B）6", "text"),
        L1Line("P1L004", 1, 4, 4, "2. 计算：√4 + √9 =", "text"),
        L1Line("P1L005", 1, 5, 5, "（A）3", "text"),
        L1Line("P1L006", 1, 6, 6, "参考答案", "text"),
        L1Line("P1L007", 1, 7, 7, "（1）A （2）B", "text"),
    ]
    return L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source="native",
        total_pages=1,
    )


def test_match_answer_from_table():
    """从答案表匹配答案。"""
    doc = _make_doc_with_answer_table()
    questions = [
        SlicedQuestion(
            question_number="1",
            question_type="single_choice",
            stem="已知函数f(x)=2x+1，则f(3)=",
            options=[{"label": "A", "text": "5"}, {"label": "B", "text": "6"}],
        ),
        SlicedQuestion(
            question_number="2",
            question_type="single_choice",
            stem="计算：√4 + √9 =",
            options=[{"label": "A", "text": "3"}],
        ),
    ]

    result = match_answers(questions, doc)
    assert result[0].answer == "A"
    assert result[0].answer_provenance.source == "document_answer_table"
    assert result[1].answer == "B"
    assert result[1].answer_provenance.source == "document_answer_table"


def test_match_no_answer_returns_llm_fallback():
    """无答案时返回 LLM 兜底。"""
    doc = _make_doc_with_answer_table()
    questions = [
        SlicedQuestion(
            question_number="99",
            question_type="single_choice",
            stem="不存在的题目",
            options=[],
        ),
    ]

    result = match_answers(questions, doc)
    assert result[0].answer is None
    assert result[0].answer_provenance.source == "llm_fallback"


def test_match_inline_answer():
    """从题后【答案】标记匹配。"""
    lines = [
        L1Line("P1L001", 1, 1, 1, "1. 已知函数f(x)=2x+1，则f(3)=", "text"),
        L1Line("P1L002", 1, 2, 2, "【答案】A", "text"),
    ]
    doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source="native",
        total_pages=1,
    )

    questions = [
        SlicedQuestion(
            question_number="1",
            question_type="single_choice",
            stem="已知函数f(x)=2x+1，则f(3)=",
            options=[],
        ),
    ]

    result = match_answers(questions, doc)
    assert result[0].answer == "A"
    assert result[0].answer_provenance.source == "document_inline_answer"


def test_match_inline_explanation():
    """从题后【详解】标记匹配。"""
    lines = [
        L1Line("P1L001", 1, 1, 1, "(1) question text", "text"),
        L1Line("P1L002", 1, 2, 2, "question text continued", "text"),
        L1Line("P1L003", 1, 3, 3, "explanation content here", "text"),
    ]
    doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source="native",
        total_pages=1,
    )

    questions = [
        SlicedQuestion(
            question_number="1",
            question_type="single_choice",
            stem="question text",
            options=[],
        ),
    ]

    result = match_answers(questions, doc)
    # Without 【详解】 marker, explanation is empty but provenance is set
    assert result[0].explanation_provenance.source == "llm_fallback"


def test_provenance_always_present():
    """provenance 始终非空。"""
    doc = _make_doc_with_answer_table()
    questions = [
        SlicedQuestion(
            question_number="1",
            question_type="single_choice",
            stem="test",
            options=[],
        ),
    ]

    result = match_answers(questions, doc)
    assert result[0].answer_provenance is not None
    assert result[0].explanation_provenance is not None


def test_answer_table_with_parenthesized_answers():
    """答案含括号时按题号边界切分，不能丢失。"""
    lines = [
        L1Line("P1L001", 1, 1, 1, "1. 题目一", "text"),
        L1Line("P1L002", 1, 2, 2, "参考答案", "text"),
        L1Line(
            "P1L003", 1, 3, 3,
            "(11)$\\frac{\\sqrt{2}}{2}$ "
            "(12)$(-\\infty,0)\\bigcup(0,1)$ （13）7",
            "text",
        ),
        L1Line("P1L004", 1, 4, 4, "（14）0（答案不唯一）", "text"),
    ]
    doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source="native",
        total_pages=1,
    )
    questions = [
        SlicedQuestion("11", "fill_in", stem="11"),
        SlicedQuestion("12", "fill_in", stem="12"),
        SlicedQuestion("13", "fill_in", stem="13"),
        SlicedQuestion("14", "fill_in", stem="14"),
    ]

    result = match_answers(questions, doc)
    assert result[0].answer == "$\\frac{\\sqrt{2}}{2}$"
    assert result[1].answer == "$(-\\infty,0)\\bigcup(0,1)$"
    assert result[2].answer == "7"
    assert result[3].answer == "0（答案不唯一）"


def test_answer_table_stops_at_solution_section():
    """答案表在解答题区停止，不把解答题标题解析成短答案。"""
    lines = [
        L1Line("P1L001", 1, 1, 1, "1. 题目一", "text"),
        L1Line("P1L002", 1, 2, 2, "参考答案", "text"),
        L1Line("P1L003", 1, 3, 3, "（1）A", "text"),
        L1Line("P1L004", 1, 4, 4, "三、解答题(共5小题，共70分）", "text"),
        L1Line("P1L005", 1, 5, 5, "(17）(共13分)", "text"),
    ]
    doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source="native",
        total_pages=1,
    )
    questions = [SlicedQuestion("17", "解答题", stem="17")]

    result = match_answers(questions, doc)
    assert result[0].answer is None
    assert result[0].answer_provenance.source == "llm_fallback"

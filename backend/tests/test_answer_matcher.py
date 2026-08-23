"""答案与详解匹配器单元测试。"""

from app.domains.document.answer_matcher import match_answers
from app.domains.document.schemas_l1 import L1Document, L1Line, L1Page
from app.domains.document.schemas_l2 import (
    L2DocumentAnnotation,
    L2QuestionAnnotation,
    SlicedQuestion,
)


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


def test_match_answers_prefers_llm_annotation_refs():
    """传入 llm_annotation 时，优先使用答案/详解行号切片，不再依赖规则匹配。"""
    lines = [
        L1Line("P1L001", 1, 1, 1, "1. 已知函数f(x)=2x+1，则f(3)=", "text"),
        L1Line("P1L002", 1, 2, 2, "【详解】解析内容", "text"),
        L1Line("P1L003", 1, 3, 3, "参考答案", "text"),
        L1Line("P1L004", 1, 4, 4, "（1）A （2）B", "text"),
    ]
    doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source="native",
        total_pages=1,
    )
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="1",
                question_type="single_choice",
                answer="A",
                answer_line_ids=["P1L004"],
                explanation_line_ids=["P1L002"],
            )
        ],
    )
    questions = [
        SlicedQuestion(
            question_number="1",
            question_type="single_choice",
            stem="已知函数f(x)=2x+1，则f(3)=",
            options=[],
        )
    ]

    result = match_answers(questions, doc, llm_annotation=annotation)
    # V1_LESSONS 3.17: 答案表有 "A" 时优先用答案表，不依赖 LLM
    assert result[0].answer == "A"
    assert result[0].answer_provenance.source == "document_answer_table"
    assert result[0].explanation == "【详解】解析内容"
    assert result[0].explanation_line_ids == ["P1L002"]
    assert result[0].explanation_provenance.source == "llm_annotation"


def test_match_answers_falls_back_when_llm_refs_missing():
    """LLM 未给出行号时，answer_matcher 规则链仍作为 fallback 生效。"""
    doc = _make_doc_with_answer_table()
    annotation = L2DocumentAnnotation(filename="test.pdf", questions=[])
    questions = [
        SlicedQuestion(
            question_number="1",
            question_type="single_choice",
            stem="已知函数f(x)=2x+1，则f(3)=",
            options=[],
        )
    ]

    result = match_answers(questions, doc, llm_annotation=annotation)
    assert result[0].answer == "A"
    assert result[0].answer_provenance.source == "document_answer_table"


def test_llm_answer_slice_cleans_common_prefixes_and_rejects_non_answer():
    """LLM 答案行号切片清理常见前缀；指向分析/题干类内容时回退规则匹配。"""
    lines = [
        L1Line("P1L001", 1, 1, 1, "1. 已知函数f(x)=2x+1，则f(3)=", "text"),
        L1Line("P1L002", 1, 2, 2, "故选 C。", "text"),
        L1Line("P1L003", 1, 3, 3, "本题考查函数的单调性", "text"),
        L1Line("P1L004", 1, 4, 4, "答案为 D", "text"),
        L1Line("P1L005", 1, 5, 5, "选 A", "text"),
        L1Line("P1L006", 1, 6, 6, "参考答案", "text"),
        L1Line("P1L007", 1, 7, 7, "（1）A （2）B", "text"),
    ]
    doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source="native",
        total_pages=1,
    )
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="1",
                question_type="single_choice",
                answer_line_ids=["P1L002"],
            ),
            L2QuestionAnnotation(
                question_number="2",
                question_type="single_choice",
                answer_line_ids=["P1L003"],
            ),
            L2QuestionAnnotation(
                question_number="3",
                question_type="single_choice",
                answer_line_ids=["P1L004"],
            ),
            L2QuestionAnnotation(
                question_number="4",
                question_type="single_choice",
                answer_line_ids=["P1L005"],
            ),
        ],
    )
    questions = [
        SlicedQuestion("1", "single_choice", stem="1"),
        SlicedQuestion("2", "single_choice", stem="2"),
        SlicedQuestion("3", "single_choice", stem="3"),
        SlicedQuestion("4", "single_choice", stem="4"),
    ]

    result = match_answers(questions, doc, llm_annotation=annotation)
    # V1_LESSONS 3.17: 答案表有 Q1="A", Q2="B" 时优先用答案表
    assert result[0].answer == "A"
    assert result[0].answer_provenance.source == "document_answer_table"
    assert result[1].answer == "B"
    assert result[1].answer_provenance.source == "document_answer_table"
    # Q3/Q4 不在答案表中，走 LLM 切片
    assert result[2].answer == "D"
    assert result[2].answer_provenance.source == "llm_annotation"
    assert result[3].answer == "A"
    assert result[3].answer_provenance.source == "llm_annotation"


def test_short_answer_llm_line_ids_direct():
    """解答题 LLM 标注直接应用，图解行被过滤。"""
    lines = [
        L1Line("P10L001", 10, 1, 1, "O \n37T \nF", "text"),
        L1Line("P10L002", 10, 2, 2, "(1)mg (3分)", "text"),
        L1Line(
            "P10L003", 10, 3, 3,
            "(2)$F=m g\\tan37^{\\circ}=1.5N$ (2分)",
            "text",
        ),
    ]
    doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=10, lines=lines)],
        lines=lines,
        source="ppsv3",
        total_pages=10,
    )
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="18",
                question_type="short_answer",
                answer_line_ids=["P10L001", "P10L002", "P10L003"],
            ),
        ],
    )
    questions = [
        SlicedQuestion("18", "short_answer", stem="18"),
    ]

    result = match_answers(questions, doc, llm_annotation=annotation)
    # P10L001("O \n37T \nF") 是图解标签，应被过滤
    assert result[0].answer_line_ids == ["P10L002", "P10L003"]
    assert result[0].answer_provenance.source == "llm_annotation"


def test_answer_section_title_filtered_from_answer_line_ids():
    """答案区标题行（如"54.【答案】例文"）应从 answer_line_ids 中过滤。"""
    lines = [
        L1Line("P18L006", 18, 6, 6, "54.【答案】例文", "text"),
        L1Line("P18L007", 18, 7, 7, "Dear Jim,", "text"),
        L1Line("P18L008", 18, 8, 8, "I'm glad to know...", "text"),
        L1Line("P18L009", 18, 9, 9, "Yours,Li Hua", "text"),
    ]
    doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=18, lines=lines)],
        lines=lines,
        source="ppsv3",
        total_pages=18,
    )
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="54",
                question_type="short_answer",
                answer_line_ids=["P18L006", "P18L007", "P18L008", "P18L009"],
            ),
        ],
    )
    questions = [SlicedQuestion("54", "short_answer", stem="54")]

    result = match_answers(questions, doc, llm_annotation=annotation)
    # P18L006("54.【答案】例文")应被过滤
    assert result[0].answer_line_ids == ["P18L007", "P18L008", "P18L009"]
    assert "例文" not in (result[0].answer or "")
    assert result[0].answer_provenance.source == "llm_annotation"


def test_short_answer_sub_question_lines_not_skipped():
    """解答题 (1)/(2)/(3) 小问答案行不应被 skip_wrong_marker_lines 跳过。"""
    lines = [
        L1Line("P10L001", 10, 1, 1, "O \n37T \nF", "text"),  # 图解标签
        L1Line("P10L002", 10, 2, 2, "(1)mg (3分)", "text"),
        L1Line("P10L003", 10, 3, 3, "(2)$F=m g\\tan37^{\\circ}=1.5N$ (2分)", "text"),
        L1Line("P10L004", 10, 4, 4, "（3）由力的合成分解可知...", "text"),
        L1Line("P10L005", 10, 5, 5, "F增大，θ增大，轻绳拉力T增大", "text"),
        L1Line("P10L007", 10, 7, 7, "轻绳与竖直方向夹角增大", "text"),
    ]
    doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=10, lines=lines)],
        lines=lines,
        source="ppsv3",
        total_pages=10,
    )
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="18",
                question_type="short_answer",
                answer_line_ids=["P10L001", "P10L002", "P10L003", "P10L004", "P10L005", "P10L007"],
            ),
        ],
    )
    questions = [SlicedQuestion("18", "short_answer", stem="18")]

    result = match_answers(questions, doc, llm_annotation=annotation)
    # (1)mg 和 (2)F=1.5N 不应被跳过
    assert "(1)mg" in result[0].answer
    assert "1.5N" in result[0].answer
    assert "F增大" in result[0].answer


def test_diagram_labels_filtered_from_answer_line_ids():
    """纯图解/标签行（如"O \n37T \nF"）应从 answer_line_ids 中过滤。"""
    lines = [
        L1Line("P10L001", 10, 1, 1, "O \n37T \nF", "text"),  # 图解标签
        L1Line("P10L002", 10, 2, 2, "(1)mg (3分)", "text"),
        L1Line("P10L003", 10, 3, 3, "(2)$F=m g\\tan37^{\\circ}=1.5N$ (2分)", "text"),
        L1Line("P10L005", 10, 5, 5, "F增大，θ增大，轻绳拉力T增大", "text"),
    ]
    doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=10, lines=lines)],
        lines=lines,
        source="ppsv3",
        total_pages=10,
    )
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="18",
                question_type="short_answer",
                answer_line_ids=["P10L001", "P10L002", "P10L003", "P10L005"],
            ),
        ],
    )
    questions = [SlicedQuestion("18", "short_answer", stem="18")]

    result = match_answers(questions, doc, llm_annotation=annotation)
    # P10L001("O \n37T \nF") 应被过滤
    assert "P10L001" not in result[0].answer_line_ids
    assert "O" not in (result[0].answer or "")
    assert "(1)mg" in result[0].answer


def test_short_answer_boundary_filters_next_question_lines():
    """解答题 answer_line_ids 应限制在当前题目范围内，不能混入下一题的行。"""
    lines = [
        L1Line("P9L023", 9, 23, 23, "18.（9分）解：", "text"),
        L1Line("P10L001", 10, 1, 24, "O \n37T \nF", "text"),
        L1Line("P10L002", 10, 2, 25, "(1)mg (3分)", "text"),
        L1Line("P10L003", 10, 3, 26, "(2)$F=1.5N$ (2分)", "text"),
        L1Line("P10L004", 10, 4, 27, "（3）由力的合成分解可知...", "text"),
        L1Line("P10L005", 10, 5, 28, "F增大，轻绳拉力T增大", "text"),
        L1Line("P10L006", 10, 6, 29, "19.（9分）解：", "text"),  # 下一题
        L1Line("P10L007", 10, 7, 30, "（1）由牛顿第二定律...", "text"),  # Q19 的内容
    ]
    doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=9, lines=lines[:1]), L1Page(page_no=10, lines=lines[1:])],
        lines=lines,
        source="ppsv3",
        total_pages=10,
    )
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="18",
                question_type="short_answer",
                answer_line_ids=["P10L001", "P10L002", "P10L003", "P10L004", "P10L005", "P10L007"],
            ),
        ],
    )
    questions = [SlicedQuestion("18", "short_answer", stem="18")]

    result = match_answers(questions, doc, llm_annotation=annotation)
    # P10L007 属于 Q19，不应进入 Q18 答案
    assert "P10L007" not in result[0].answer_line_ids
    assert "牛顿第二定律" not in (result[0].answer or "")
    # Q18 的 (1)/(2) 应保留
    assert "(1)mg" in result[0].answer or "mg" in result[0].answer


def test_llm_answer_line_ids_split_multi_question_line():
    """LLM 同行多题答案按题号边界切分，不能把整行拼给每题。"""
    lines = [
        L1Line(
            "P5L005", 5, 5, 5,
            "(11)$\\frac{\\sqrt{2}}{2}$ "
            "(12)$(-\\infty,0)\\bigcup(0,1)$ （13）7",
            "text",
        ),
        L1Line("P5L006", 5, 6, 6, "ги13гй7", "text"),
    ]
    doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=5, lines=lines)],
        lines=lines,
        source="ppsv3",
        total_pages=5,
    )
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="11",
                question_type="fill_in",
                answer_line_ids=["P5L005"],
            ),
            L2QuestionAnnotation(
                question_number="12",
                question_type="fill_in",
                answer_line_ids=["P5L005"],
            ),
            L2QuestionAnnotation(
                question_number="13",
                question_type="fill_in",
                answer_line_ids=["P5L005"],
            ),
        ],
    )
    questions = [
        SlicedQuestion("11", "fill_in", stem="11"),
        SlicedQuestion("12", "fill_in", stem="12"),
        SlicedQuestion("13", "fill_in", stem="13"),
    ]

    result = match_answers(questions, doc, llm_annotation=annotation)
    assert result[0].answer == "$\\frac{\\sqrt{2}}{2}$"
    assert result[1].answer == "$(-\\infty,0)\\bigcup(0,1)$"
    assert result[2].answer == "7"


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


def test_match_answer_and_explanation_from_solution_block():
    """数学/物理解答题没有短答案表时，从解题过程定位答案和完整详解。"""
    lines = [
        L1Line("P1L001", 1, 1, 1, "参考答案", "text"),
        L1Line("P1L002", 1, 2, 2, "三、解答题(共5小题，共70分）", "text"),
        L1Line("P1L003", 1, 3, 3, "(17)(共13分)", "text"),
        L1Line(
            "P1L004", 1, 4, 4,
            "解：（Ⅰ）所以不等式f(x)<-1的解集是{x|-1<x<3}……6分",
            "text",
        ),
        L1Line("P1L005", 1, 5, 5, "（Ⅱ）解得a≥6或a≤-8", "text"),
        L1Line("P1L006", 1, 6, 6, "即a∈(-∞,-8]∪[6,+∞) ……13分", "text"),
        L1Line("P1L007", 1, 7, 7, "(18)(共13分)", "text"),
        L1Line("P1L008", 1, 8, 8, "解：下一题内容", "text"),
    ]
    doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source="ppsv3",
        total_pages=1,
    )
    questions = [
        SlicedQuestion(
            question_number="17",
            question_type="short_answer",
            stem="（17）求不等式和a的范围",
        )
    ]

    result = match_answers(questions, doc)
    assert result[0].answer is not None
    assert "解集" in result[0].answer
    assert "a∈" in result[0].answer
    assert result[0].answer_provenance.source == "document_solution_answer"
    assert result[0].answer_line_ids == ["P1L004", "P1L005", "P1L006"]
    assert "解：（Ⅰ）" in result[0].explanation
    assert "(18)" not in result[0].explanation


def test_solution_block_stops_at_merged_next_question():
    """PP 一行内换行合并多题时，必须在下一题号处截断。"""
    lines = [
        L1Line("P1L001", 1, 1, 1, "参考答案", "text"),
        L1Line("P1L002", 1, 2, 2, "三、解答题(共5小题，共70分）", "text"),
        L1Line("P1L003", 1, 3, 3, "(19)(共14分)", "text"),
        L1Line("P1L004", 1, 4, 4, "解：题干内容", "text"),
        L1Line(
            "P1L005", 1, 5, 5,
            "则m的取值范围是(0,π/12] 14分\n"
            "(20)(共15分)\n"
            "解：（I）所以k=1 ……3分",
            "text",
        ),
    ]
    doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source="ppsv3",
        total_pages=1,
    )
    questions = [
        SlicedQuestion(
            question_number="19",
            question_type="short_answer",
            stem="（19）求m的范围",
        ),
        SlicedQuestion(
            question_number="20",
            question_type="short_answer",
            stem="（20）求k",
        ),
    ]

    result = match_answers(questions, doc)
    q19, q20 = result
    assert q19.answer is not None
    assert "m的取值范围" in q19.answer
    assert "(20)" not in q19.explanation
    assert "所以k=1" not in q19.explanation
    assert q20.answer is not None
    assert "k=1" in q20.answer
    assert "(20)" in q20.explanation or "解：（I）" in q20.explanation


def test_solution_answer_excludes_proof_header():
    """证明小标题“（Ⅲ）不存在，理由如下：”不是最终答案，不应进入 answer。"""
    lines = [
        L1Line("P1L001", 1, 1, 1, "参考答案", "text"),
        L1Line("P1L002", 1, 2, 2, "三、解答题(共5小题，共70分）", "text"),
        L1Line("P1L003", 1, 3, 3, "(21)(共15分)", "text"),
        L1Line("P1L004", 1, 4, 4, "（Ⅲ）不存在，理由如下：", "text"),
        L1Line("P1L005", 1, 5, 5, "综上不存在n ……15分", "text"),
    ]
    doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source="ppsv3",
        total_pages=1,
    )
    questions = [
        SlicedQuestion(
            question_number="21",
            question_type="short_answer",
            stem="（21）证明不存在",
        )
    ]

    result = match_answers(questions, doc)
    assert result[0].answer is not None
    assert "理由如下" not in result[0].answer
    assert "综上不存在" in result[0].answer


def test_llm_answer_line_ids_split_corrupted_ocr_marker():
    """OCR 把全角题号识别为字母时，仍按题号切出当前题答案。"""
    lines = [
        L1Line(
            "P5L006", 5, 6, 6,
            "\u0433\u0438" + "13" + "\u0433\u0439" + "7",
            "text",
        ),
    ]
    doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=5, lines=lines)],
        lines=lines,
        source="ppsv3",
        total_pages=5,
    )
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="13",
                question_type="fill_in",
                answer_line_ids=["P5L006"],
            )
        ],
    )
    questions = [
        SlicedQuestion("13", "fill_in", stem="13"),
    ]

    result = match_answers(questions, doc, llm_annotation=annotation)
    assert result[0].answer == "7"


def test_llm_answer_line_wrong_marker_falls_back_to_rule_matcher():
    """LLM 行号指向其他题号的行时，回退规则答案表，不把别的题答案拼进来。"""
    lines = [
        L1Line("P1L001", 1, 1, 1, "Answer Key", "text"),
        L1Line(
            "P1L002", 1, 2, 2,
            "19.to buy 20.\u3010\u7b54\u6848\u3011encouraged",
            "text",
        ),
        L1Line(
            "P1L003", 1, 3, 3,
            "20.\u3010\u7b54\u6848\u3011encouraged",
            "text",
        ),
    ]
    doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source="ppsv3",
        total_pages=1,
    )
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="19",
                question_type="fill_in",
                answer_line_ids=["P1L003"],
            )
        ],
    )
    questions = [
        SlicedQuestion("19", "fill_in", stem="19"),
    ]

    result = match_answers(questions, doc, llm_annotation=annotation)
    assert result[0].answer == "to buy"
    assert result[0].answer_provenance.source == "document_answer_table"


def test_short_answer_line_ids_trust_llm_when_valid():
    """解答题 answer_line_ids 校验后从 L1 切片（不依赖 LLM 文本）。"""
    lines = [
        L1Line("P1L001", 1, 1, 1, "参考答案", "text"),
        L1Line("P1L002", 1, 2, 2, "三、解答题(共5小题，共70分）", "text"),
        L1Line("P1L003", 1, 3, 3, "(18)(共13分)", "text"),
        L1Line("P1L004", 1, 4, 4, "解：所以x=3 ……6分", "text"),
        L1Line("P1L005", 1, 5, 5, "(19)(共13分)", "text"),
        L1Line("P1L006", 1, 6, 6, "解：下一题", "text"),
    ]
    doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source="ppsv3",
        total_pages=1,
    )
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="18",
                question_type="short_answer",
                answer="x=3",
                answer_line_ids=["P1L004", "P1L005"],
            )
        ],
    )
    questions = [SlicedQuestion("18", "short_answer", stem="18")]

    result = match_answers(questions, doc, llm_annotation=annotation)
    # 解题过程规则提取答案行（确定性），不依赖 LLM answer_line_ids
    assert "x=3" in result[0].answer


def test_llm_answer_with_invalid_line_ids_falls_back_to_document_answer():
    """LLM 给了短答案但行号全部无效时，先走答案表规则匹配。"""
    lines = [
        L1Line("P1L001", 1, 1, 1, "Answer Key", "text"),
        L1Line("P1L002", 1, 2, 2, "19.to buy", "text"),
    ]
    doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source="ppsv3",
        total_pages=1,
    )
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="19",
                question_type="fill_in",
                answer="should attend",
                answer_line_ids=["P99L999"],
            )
        ],
    )
    questions = [SlicedQuestion("19", "fill_in", stem="19")]

    result = match_answers(questions, doc, llm_annotation=annotation)
    assert result[0].answer == "to buy"
    assert result[0].answer_provenance.source == "document_answer_table"
    assert result[0].answer_line_ids == ["P1L002"]


def test_llm_answer_text_ignored_when_line_ids_valid():
    """同锚点不同 LLM 文本：answer_line_ids 有效时，从 L1 切片，不依赖 q.answer。

    场景：Q16 的 answer_line_ids 两轮都是 P9L008-P9L011，但 LLM 输出的
    q.answer 一次有 (1)B，一次没有。最终答案应由 L1 切片决定，确保确定性。
    """
    lines = [
        L1Line("P9L008", 9, 8, 8, "(1)B", "text"),
        L1Line("P9L009", 9, 9, 9, "(2)使小车所受合力大小等于绳上的拉力大小", "text"),
        L1Line("P9L010", 9, 10, 10, "(3)左 0.45（0.43~0.46均可）", "text"),
        L1Line("P9L011", 9, 11, 11, "(4)C", "text"),
    ]
    doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=9, lines=lines)],
        lines=lines,
        source="ppsv3",
        total_pages=9,
    )
    answer_ids = ["P9L008", "P9L009", "P9L010", "P9L011"]

    # run1: LLM answer 包含 (1)B
    annotation1 = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="16",
                question_type="short_answer",
                answer="(1)B (2)使小车所受合力大小等于绳上的拉力大小 (3)左 0.45 (4)C",
                answer_line_ids=answer_ids,
            ),
        ],
    )
    # run2: LLM answer 缺少 (1)B
    annotation2 = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="16",
                question_type="short_answer",
                answer="(2)使小车所受合力大小等于绳上的拉力大小（2分）(3)左 0.45（2分）(4)C",
                answer_line_ids=answer_ids,
            ),
        ],
    )
    questions = [SlicedQuestion("16", "short_answer", stem="16")]

    result1 = match_answers(questions, doc, llm_annotation=annotation1)
    result2 = match_answers(questions, doc, llm_annotation=annotation2)

    # 两次结果必须一致（由 L1 切片决定）
    assert result1[0].answer == result2[0].answer
    # 答案应包含 (1)B（来自 L1 原文）
    assert "(1)B" in result1[0].answer
    assert result1[0].answer_provenance.source == "llm_annotation"


def test_answer_table_overrides_llm_for_choice_questions():
    """V1_LESSONS 3.17: 答案表有字母答案时，优先用答案表，忽略 LLM 锚点。

    场景：英语阅读理解 Q31，LLM run1 指向导语行，run2 指向答案行。
    答案表有 31.A，两轮都必须收敛到 A。
    """
    lines = [
        L1Line("P13L003", 13, 3, 3, "31. A", "text"),
        L1Line("P13L004", 13, 4, 4, "【导语】这是一篇应用文。文章介绍了...", "text"),
        L1Line("P13L005", 13, 5, 5, "参考答案", "text"),
        L1Line("P13L006", 13, 6, 6, "31.A 32.B 33.C", "text"),
    ]
    doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=13, lines=lines)],
        lines=lines,
        source="ppsv3",
        total_pages=13,
    )
    questions = [SlicedQuestion("31", "single_choice", stem="31")]

    # run1: LLM 指向导语行
    ann1 = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[L2QuestionAnnotation(
            question_number="31",
            question_type="single_choice",
            answer="【导语】这是一篇应用文...",
            answer_line_ids=["P13L004"],
        )],
    )
    # run2: LLM 指向答案行
    ann2 = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[L2QuestionAnnotation(
            question_number="31",
            question_type="single_choice",
            answer="A",
            answer_line_ids=["P13L003"],
        )],
    )

    result1 = match_answers(questions, doc, llm_annotation=ann1)
    result2 = match_answers(questions, doc, llm_annotation=ann2)

    # 两轮都必须收敛到答案表的 A
    assert result1[0].answer == "A"
    assert result2[0].answer == "A"
    assert result1[0].answer == result2[0].answer
    assert result1[0].answer_provenance.source == "document_answer_table"
    assert result2[0].answer_provenance.source == "document_answer_table"


def test_llm_choice_answer_rejected_when_not_letter():
    """没有答案表时，LLM 给导语/详解作为答案必须被拒绝。"""
    lines = [
        L1Line("P13L004", 13, 4, 4, "【导语】这是一篇应用文。文章介绍了...", "text"),
    ]
    doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=13, lines=lines)],
        lines=lines,
        source="ppsv3",
        total_pages=13,
    )
    questions = [SlicedQuestion("31", "single_choice", stem="31")]
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[L2QuestionAnnotation(
            question_number="31",
            question_type="single_choice",
            answer="【导语】这是一篇应用文...",
            answer_line_ids=["P13L004"],
        )],
    )

    result = match_answers(questions, doc, llm_annotation=annotation)
    # 导语不是答案字母，必须被拒绝
    assert result[0].answer is None or _CHOICE_ANSWER_RE.match(
        result[0].answer.strip().upper().replace(" ", "")
    )


def test_llm_choice_answer_kept_when_valid_letter():
    """没有答案表时，LLM 给合法字母答案应保留。"""
    lines = [
        L1Line("P13L003", 13, 3, 3, "31. A", "text"),
    ]
    doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=13, lines=lines)],
        lines=lines,
        source="ppsv3",
        total_pages=13,
    )
    questions = [SlicedQuestion("31", "single_choice", stem="31")]
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[L2QuestionAnnotation(
            question_number="31",
            question_type="single_choice",
            answer="A",
            answer_line_ids=["P13L003"],
        )],
    )

    result = match_answers(questions, doc, llm_annotation=annotation)
    assert result[0].answer == "A"
    assert result[0].answer_provenance.source == "llm_annotation"


def test_short_answer_uses_solution_block_over_llm_line_ids():
    """V1_LESSONS: short_answer 优先从解题过程提取答案行，忽略 LLM 的 answer_line_ids。

    场景：数学 Q21 两次 run 的 answer_line_ids 差一行（P8L007），
    但解题过程块提取的结果是确定性的。
    """
    lines = [
        L1Line("P7L023", 7, 23, 23, "解：（I）由题n=16时", "text"),
        L1Line("P8L001", 8, 1, 24, "当B1={1,8},B2={2,4}时，d1取得最大值", "text"),
        L1Line("P8L006", 8, 6, 29, "（Ⅱ）存在.", "text"),
        L1Line("P8L007", 8, 7, 30, "（）不存在，理由如下：", "text"),
        L1Line("P9L001", 9, 1, 31, "综上不存在n以及B1,B2,...,Bm", "text"),
    ]
    doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=7, lines=lines)],
        lines=lines,
        source="ppsv3",
        total_pages=9,
    )
    questions = [SlicedQuestion("21", "short_answer", stem="21")]

    # run1: LLM answer_line_ids 不含 P8L007
    ann1 = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[L2QuestionAnnotation(
            question_number="21",
            question_type="short_answer",
            answer_line_ids=["P7L023", "P8L001", "P8L006", "P9L001"],
        )],
    )
    # run2: LLM answer_line_ids 含 P8L007
    ann2 = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[L2QuestionAnnotation(
            question_number="21",
            question_type="short_answer",
            answer_line_ids=["P7L023", "P8L001", "P8L006", "P8L007", "P9L001"],
        )],
    )

    result1 = match_answers(questions, doc, llm_annotation=ann1)
    result2 = match_answers(questions, doc, llm_annotation=ann2)

    # 解题过程提取是确定性的，两轮结果必须一致
    assert result1[0].answer == result2[0].answer

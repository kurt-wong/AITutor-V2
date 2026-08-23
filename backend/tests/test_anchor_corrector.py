"""锚点校验器单元测试（LLM 驱动，代码只校验）。"""

from app.domains.document.anchor_corrector import correct_anchors
from app.domains.document.schemas_l1 import L1Document, L1Line, L1Page
from app.domains.document.schemas_l2 import L2DocumentAnnotation, L2QuestionAnnotation


def _make_doc_with_questions() -> L1Document:
    """构造包含括号题号和选项的 L1 文档。"""
    lines = [
        L1Line("P1L001", 1, 1, 1, "一、选择题", "text"),
        L1Line("P1L002", 1, 2, 2, "（2）下列函数中", "text"),
        L1Line("P1L003", 1, 3, 3, "（A）y = x", "text"),
        L1Line("P1L004", 1, 4, 4, "（B）y = x²", "text"),
        L1Line("P1L005", 1, 5, 5, "（C）y = 2x", "text"),
        L1Line("P1L006", 1, 6, 6, "（D）y = log₂x", "text"),
    ]
    return L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source="native",
        total_pages=1,
    )


def test_exact_anchor_for_paren_question():
    """(2) 格式题号校验通过。"""
    doc = _make_doc_with_questions()
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="2",
                question_type="single_choice",
                stem_line_ids=["P1L002"],
                options_line_ids={"A": ["P1L003"]},
            )
        ],
    )

    result = correct_anchors(annotation, doc)
    stem_anchor = result.corrected_anchors[0]
    assert stem_anchor.anchor_status == "exact"
    assert stem_anchor.corrected_line_ids == ["P1L002"]


def test_exact_anchor_for_option():
    """选项行号首行匹配标签时校验通过。"""
    doc = _make_doc_with_questions()
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="2",
                question_type="single_choice",
                stem_line_ids=["P1L002"],
                options_line_ids={"A": ["P1L003"]},
            )
        ],
    )

    result = correct_anchors(annotation, doc)
    opt_anchor = [a for a in result.corrected_anchors if a.field == "option_A"][0]
    assert opt_anchor.anchor_status == "exact"
    assert opt_anchor.corrected_line_ids == ["P1L003"]


def test_exact_anchor_for_dot_question_and_g_option():
    """点号题号和 A-G 选项标签均支持。"""
    lines = [
        L1Line("P1L001", 1, 1, 1, "37. 七选五题目", "text"),
        L1Line("P1L002", 1, 2, 2, "A. one", "text"),
        L1Line("P1L003", 1, 3, 3, "B. two", "text"),
        L1Line("P1L004", 1, 4, 4, "C. three", "text"),
        L1Line("P1L005", 1, 5, 5, "D. four", "text"),
        L1Line("P1L006", 1, 6, 6, "E. five", "text"),
        L1Line("P1L007", 1, 7, 7, "F. six", "text"),
        L1Line("P1L008", 1, 8, 8, "G. seven", "text"),
    ]
    doc = L1Document(
        filename="english.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source="native",
        total_pages=1,
    )
    annotation = L2DocumentAnnotation(
        filename="english.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="37",
                question_type="single_choice",
                stem_line_ids=["P1L001"],
                options_line_ids={
                    label: [f"P1L00{idx}"]
                    for idx, label in enumerate("ABCDEFG", 2)
                },
            )
        ],
    )

    result = correct_anchors(annotation, doc)
    statuses = [a.anchor_status for a in result.corrected_anchors]
    assert statuses[0] == "exact"
    assert all(s == "exact" for s in statuses[1:]), statuses


def test_empty_stem_retry():
    """空行号标记 retry，不猜测题干起点。"""
    doc = _make_doc_with_questions()
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="2",
                question_type="single_choice",
                stem_line_ids=[],
                options_line_ids={},
            )
        ],
    )

    result = correct_anchors(annotation, doc)
    stem_anchor = result.corrected_anchors[0]
    assert stem_anchor.anchor_status == "retry"
    assert stem_anchor.corrected_line_ids == []
    assert result.questions[0].stem_line_ids == []


def test_invalid_stem_retry():
    """无效行号标记 retry，不做同页吸附。"""
    doc = _make_doc_with_questions()
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="2",
                question_type="single_choice",
                stem_line_ids=["P1L999"],
                options_line_ids={},
            )
        ],
    )

    result = correct_anchors(annotation, doc)
    assert result.corrected_anchors[0].anchor_status == "retry"
    assert result.questions[0].stem_line_ids == []


def test_stem_in_answer_section_retry():
    """题干首行位于答案区时标记 retry，不反推题干。"""
    lines = [
        L1Line("P1L001", 1, 1, 1, "2. 下列单位属于基本单位的是", "text"),
        L1Line("P1L002", 1, 2, 2, "A. m", "text"),
        L1Line("P1L003", 1, 3, 3, "B. s", "text"),
        L1Line("P1L004", 1, 4, 4, "C. N", "text"),
        L1Line("P1L005", 1, 5, 5, "D. A", "text"),
        L1Line("P1L006", 1, 6, 6, "参考答案", "text"),
        L1Line("P1L007", 1, 7, 7, "2. B", "text"),
    ]
    doc = L1Document(
        filename="physics.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source="native",
        total_pages=1,
    )
    annotation = L2DocumentAnnotation(
        filename="physics.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="2",
                question_type="single_choice",
                stem_line_ids=["P1L007"],
                options_line_ids={
                    "A": ["P1L002"],
                    "B": ["P1L003"],
                    "C": ["P1L004"],
                    "D": ["P1L005"],
                },
            )
        ],
    )

    result = correct_anchors(annotation, doc)
    stem_anchor = result.corrected_anchors[0]
    assert stem_anchor.anchor_status == "retry"
    assert stem_anchor.corrected_line_ids == []
    assert result.questions[0].stem_line_ids == []


def test_cross_question_stem_retry():
    """题干首行是其他题号时标记 retry，不吸附到确定性题号。"""
    lines = [
        L1Line("P1L001", 1, 1, 1, "1. 第一题", "text"),
        L1Line("P1L002", 1, 2, 2, "A. 1", "text"),
        L1Line("P1L003", 1, 3, 3, "2. 第二题", "text"),
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
                stem_line_ids=["P1L003"],
                options_line_ids={},
            )
        ],
    )

    result = correct_anchors(annotation, doc)
    assert result.corrected_anchors[0].anchor_status == "retry"


def test_wrong_option_label_retry():
    """选项 A 指向 B 行时标记 retry，不做吸附。"""
    doc = _make_doc_with_questions()
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="2",
                question_type="single_choice",
                stem_line_ids=["P1L002"],
                options_line_ids={"A": ["P1L004"]},
            )
        ],
    )

    result = correct_anchors(annotation, doc)
    opt_anchor = [a for a in result.corrected_anchors if a.field == "option_A"][0]
    assert opt_anchor.anchor_status == "retry"
    assert opt_anchor.corrected_line_ids == []


def test_llm_anchors_preserves_original():
    """llm_anchors 保留 LLM 原始输出，corrected_anchors 保存校验结果。"""
    doc = _make_doc_with_questions()
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="2",
                question_type="single_choice",
                stem_line_ids=["P1L002"],
                options_line_ids={"A": ["P1L003"]},
            )
        ],
    )

    result = correct_anchors(annotation, doc)
    stem_llm = [a for a in result.llm_anchors if a.field == "stem"][0]
    assert stem_llm.llm_line_ids == ["P1L002"]
    assert result.corrected_anchors[0].anchor_status == "exact"


def test_anchor_status_summary():
    """summary 统计 stem 的 exact/retry 数量。"""
    doc = _make_doc_with_questions()
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="2",
                question_type="single_choice",
                stem_line_ids=["P1L002"],
                options_line_ids={},
            ),
            L2QuestionAnnotation(
                question_number="3",
                question_type="single_choice",
                stem_line_ids=[],
                options_line_ids={},
            ),
        ],
    )

    result = correct_anchors(annotation, doc)
    assert result.anchor_status_summary.get("exact", 0) >= 1
    assert result.anchor_status_summary.get("retry", 0) >= 1


def test_question_start_map_prefers_bare_marker():
    """同题号多候选时，裸题号行优先于文章编号假题号。"""
    lines = [
        L1Line("P1L017", 1, 17, 1, "If you fancy doing a spot of life-saving", "text"),
        L1Line("P1L018", 1, 18, 2, "10. And, make sure your stories are interesting enough", "text"),
        L1Line("P1L063", 1, 63, 3, "D. choices", "text"),
        L1Line("P1L064", 1, 64, 4, "10.", "text"),
    ]
    doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source="native",
        total_pages=1,
    )
    from app.domains.document.anchor_corrector import _build_question_start_map
    assert _build_question_start_map(doc)[10] == "P1L064"


def test_question_start_map_keeps_first_for_answer_table():
    """答案表行不得覆盖题目区题号行。"""
    lines = [
        L1Line("P1L001", 1, 1, 1, "（1）下列函数中", "text"),
        L1Line("P1L002", 1, 2, 2, "参考答案", "text"),
        L1Line("P1L003", 1, 3, 3, "（1）A", "text"),
    ]
    doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source="native",
        total_pages=1,
    )
    from app.domains.document.anchor_corrector import _build_question_start_map
    assert _build_question_start_map(doc)[1] == "P1L001"


def test_question_number_allows_year_after_dot():
    """题号后紧跟年份数字时仍识别为题号，而不是小数。"""
    from app.domains.document.anchor_corrector import _extract_question_number
    assert _extract_question_number("3.2025年9月3日9时15分，阅兵仪式开始。") == 3
    assert _extract_question_number("3.2x") is None


def test_stem_after_solution_section_heading_is_not_answer_section():
    """“三、解答题”标题后是题目本体，不能把题干误判为答案区。"""
    from app.domains.document.anchor_corrector import _answer_section_start_order

    lines = [
        L1Line("P1L001", 1, 1, 1, "三、解答题（共5小题，共70分）", "text"),
        L1Line("P1L002", 1, 2, 2, "19. 在△ABC中，角A，B，C所对的边分别为a，b，c。", "text"),
    ]
    doc = L1Document(
        filename="math.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source="native",
        total_pages=1,
    )
    annotation = L2DocumentAnnotation(
        filename="math.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="19",
                question_type="short_answer",
                stem_line_ids=["P1L002"],
                options_line_ids={},
            )
        ],
    )

    assert _answer_section_start_order(doc) == float("inf")
    result = correct_anchors(annotation, doc)
    assert result.corrected_anchors[0].anchor_status == "exact"
    assert result.corrected_anchors[0].corrected_line_ids == ["P1L002"]

"""锚点校正器单元测试。"""

from app.domains.document.anchor_corrector import correct_anchors
from app.domains.document.schemas_l1 import L1Document, L1Line, L1Page
from app.domains.document.schemas_l2 import L2DocumentAnnotation, L2QuestionAnnotation


def _make_doc_with_questions() -> L1Document:
    """构造包含题号和选项的 L1 文档。"""
    lines = [
        L1Line("P1L001", 1, 1, 1, "一、选择题", "text"),
        L1Line("P1L002", 1, 2, 2, "（2）下列函数中", "text"),
        L1Line("P1L003", 1, 3, 3, "（A）y = x⁻¹", "text"),
        L1Line("P1L004", 1, 4, 4, "（B）y = 1/x", "text"),
        L1Line("P1L005", 1, 5, 5, "（C）y = 2⁻ˣ", "text"),
        L1Line("P1L006", 1, 6, 6, "（D）y = log₀.₅x", "text"),
    ]
    return L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source="native",
        total_pages=1,
    )


def test_exact_anchor_for_paren_question():
    """(2) 格式题号精确匹配。"""
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
    assert stem_anchor.validation_passed is True


def test_exact_anchor_for_option():
    """选项行号精确匹配选项标签。"""
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
    assert opt_anchor.validation_passed is True


def test_missing_anchor_for_empty_line_ids():
    """空行号返回 missing 状态。"""
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
    assert result.corrected_anchors[0].anchor_status == "missing"
    assert result.corrected_anchors[0].validation_passed is False


def test_missing_anchor_for_invalid_line_ids():
    """无效行号返回 missing 状态。"""
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
    assert result.corrected_anchors[0].anchor_status == "missing"


def test_retry_for_no_stable_marker():
    """无稳定标记的行号返回 retry（不是 nearest）。"""
    doc = _make_doc_with_questions()
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="99",  # 不存在的题号
                question_type="single_choice",
                stem_line_ids=["P1L001"],  # "一、选择题" 无数字题号
                options_line_ids={},
            )
        ],
    )

    result = correct_anchors(annotation, doc)
    stem_anchor = result.corrected_anchors[0]
    assert stem_anchor.anchor_status == "retry"
    assert stem_anchor.validation_passed is False


def test_corrected_anchors_written_back_to_question():
    """校正后行号回写到 question 字段。"""
    doc = _make_doc_with_questions()
    # LLM 把 A 指到了 B 的行
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="2",
                question_type="single_choice",
                stem_line_ids=["P1L002"],
                options_line_ids={"A": ["P1L004"]},  # A 应该是 P1L003
            )
        ],
    )

    result = correct_anchors(annotation, doc)
    question = result.questions[0]
    assert "P1L003" in question.options_line_ids["A"]


def test_llm_anchors_preserves_original():
    """llm_anchors 保存 LLM 原始输出。"""
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
    assert len(result.llm_anchors) > 0
    stem_llm = [a for a in result.llm_anchors if a.field == "stem"][0]
    assert stem_llm.llm_line_ids == ["P1L002"]


def test_anchor_status_summary():
    """anchor_status_summary 正确统计。"""
    doc = _make_doc_with_questions()
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="2",
                question_type="single_choice",
                stem_line_ids=["P1L002"],
                options_line_ids={"A": ["P1L003"]},
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
    assert result.anchor_status_summary.get("missing", 0) >= 1


# ── 对抗性测试：跨题归属校验 ──────────────────────────────────


def _make_doc_two_questions():
    """构造两道相邻题的 L1 文档，用于跨题归属测试。"""
    lines = [
        L1Line("P1L001", 1, 1, 1, "1. 下列函数中", "text"),
        L1Line("P1L002", 1, 2, 2, "（A）y = x", "text"),
        L1Line("P1L003", 1, 3, 3, "（B）y = x²", "text"),
        L1Line("P1L004", 1, 4, 4, "（C）y = 2x", "text"),
        L1Line("P1L005", 1, 5, 5, "（D）y = log₂x", "text"),
        L1Line("P1L006", 1, 6, 6, "2. 已知函数f(x)=", "text"),
        L1Line("P1L007", 1, 7, 7, "（A）f(1)", "text"),
        L1Line("P1L008", 1, 8, 8, "（B）f(2)", "text"),
        L1Line("P1L009", 1, 9, 9, "（C）f(3)", "text"),
        L1Line("P1L010", 1, 10, 10, "（D）f(4)", "text"),
    ]
    return L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source="native",
        total_pages=1,
    )


def test_cross_question_stem_must_not_be_exact():
    """Q1 stem 指向 Q2 的题干行 -> 必须 retry/missing，不能 exact。"""
    doc = _make_doc_two_questions()
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="1",
                question_type="single_choice",
                stem_line_ids=["P1L006"],  # 这是 Q2 的题干！
                options_line_ids={"A": ["P1L002"]},
            )
        ],
    )

    result = correct_anchors(annotation, doc)
    stem_anchor = result.corrected_anchors[0]
    assert stem_anchor.anchor_status != "exact", (
        f"Q1 stem 指向 Q2 行 P1L006 不应判为 exact，实际: {stem_anchor.anchor_status}"
    )


def test_cross_question_option_must_not_be_exact():
    """Q1 的 A 指向 Q2 的 A -> 不能 exact。"""
    doc = _make_doc_two_questions()
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="1",
                question_type="single_choice",
                stem_line_ids=["P1L001"],
                options_line_ids={"A": ["P1L007"]},  # 这是 Q2 的 A！
            )
        ],
    )

    result = correct_anchors(annotation, doc)
    opt_anchor = [a for a in result.corrected_anchors if a.field == "option_A"][0]
    assert opt_anchor.anchor_status != "exact", (
        f"Q1 option A 指向 Q2 行 P1L007 不应判为 exact，实际: {opt_anchor.anchor_status}"
    )


def test_question_number_set_on_anchors():
    """CorrectedAnchor.question_number 被正确设置。"""
    doc = _make_doc_two_questions()
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="1",
                question_type="single_choice",
                stem_line_ids=["P1L001"],
                options_line_ids={"A": ["P1L002"]},
            )
        ],
    )

    result = correct_anchors(annotation, doc)
    for anchor in result.corrected_anchors:
        assert anchor.question_number == "1", (
            f"anchor {anchor.field} question_number={anchor.question_number}, want '1'"
        )


def test_latex_continuation_does_not_shadow_question_options():
    """LaTeX 续行 0.\\end 不能被当成下一题题号。"""
    lines = [
        L1Line("P1L001", 1, 1, 1, "（7）设函数", "text"),
        L1Line("P1L002", 1, 2, 2, "0.\\end{aligned}\\right.$ 若函数", "text"),
        L1Line("P1L003", 1, 3, 3, "的取值范围是", "text"),
        L1Line("P1L004", 1, 4, 4, "(A)(0,1]", "text"),
        L1Line("P1L005", 1, 5, 5, "(B)$(0,1]\\bigcup\\{2\\}$", "text"),
        L1Line("P1L006", 1, 6, 6, "(C) [1,2]", "text"),
        L1Line("P1L007", 1, 7, 7, "(D)$\\{1\\}\\bigcup[2,+\\infty)$", "text"),
        L1Line("P1L008", 1, 8, 8, "(8）下一题", "text"),
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
                question_number="7",
                question_type="single_choice",
                stem_line_ids=["P1L001", "P1L002", "P1L003"],
                options_line_ids={
                    "A": ["P1L004"],
                    "B": ["P1L005"],
                    "C": ["P1L006"],
                    "D": ["P1L007"],
                },
            )
        ],
    )

    result = correct_anchors(annotation, doc)
    option_anchors = [
        a for a in result.corrected_anchors if a.field.startswith("option_")
    ]
    assert option_anchors, "选项锚点必须存在"
    assert all(a.anchor_status != "retry" for a in option_anchors), (
        [a.anchor_status for a in option_anchors]
    )

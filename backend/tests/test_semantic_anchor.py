"""Semantic marker resolver tests."""

from app.domains.document.anchor_corrector import correct_anchors
from app.domains.document.schemas_l1 import L1Document, L1Line, L1Page
from app.domains.document.schemas_l2 import L2DocumentAnnotation, L2QuestionAnnotation
from app.domains.document.semantic_anchor import find_marker, normalize_marker_text


def _doc(lines_text: list[str]) -> L1Document:
    lines = [
        L1Line(
            line_id=f"P1L{index:03d}",
            page_no=1,
            line_no_in_page=index,
            order=index,
            text=text,
            block_type="text",
        )
        for index, text in enumerate(lines_text, start=1)
    ]
    return L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source="ppsv3",
        total_pages=1,
    )


def test_exact_markers_resolve_stem_without_llm_line_ids():
    doc = _doc(
        [
            "1. 已知函数f(x)=2x+1",
            "则f(3)=",
            "A. 5",
            "B. 6",
            "C. 7",
            "D. 8",
            "2. 下一题",
        ]
    )
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="1",
                question_type="single_choice",
                stem_line_ids=[],
                stem_start_marker="1. 已知函数f(x)=2x+1",
                stem_end_marker="则f(3)=",
                options_line_ids={},
            )
        ],
    )

    result = correct_anchors(annotation, doc)
    stem_anchor = result.corrected_anchors[0]
    assert stem_anchor.anchor_status == "semantic"
    assert stem_anchor.corrected_line_ids == ["P1L001", "P1L002"]
    assert result.questions[0].stem_line_ids == ["P1L001", "P1L002"]


def test_fuzzy_marker_tolerates_ocr_char_difference():
    doc = _doc(
        [
            "1. 已知函数f(x)=2x+1",
            "则f(3)=5",
        ]
    )
    # LLM marker contains letter l where the source contains digit 1.
    match = find_marker("1. 已知函数f(x)=2x+l", doc.lines)
    assert match is not None
    assert match.line_id == "P1L001"
    assert match.confidence < 1.0


def test_missing_end_marker_uses_option_boundary():
    doc = _doc(
        [
            "1. 已知函数f(x)=2x+1",
            "则f(3)=",
            "A. 5",
            "B. 6",
            "2. 下一题",
        ]
    )
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="1",
                question_type="single_choice",
                stem_line_ids=[],
                stem_start_marker="1. 已知函数f(x)=2x+1",
                stem_end_marker=None,
                options_line_ids={},
            )
        ],
    )

    result = correct_anchors(annotation, doc)
    assert result.corrected_anchors[0].corrected_line_ids == ["P1L001", "P1L002"]


def test_invalid_marker_falls_back_to_llm_line_ids():
    doc = _doc(
        [
            "1. 已知函数f(x)=2x+1",
            "则f(3)=",
        ]
    )
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="1",
                question_type="short_answer",
                stem_line_ids=["P1L001", "P1L002"],
                stem_start_marker="不存在的标记",
                stem_end_marker=None,
                options_line_ids={},
            )
        ],
    )

    result = correct_anchors(annotation, doc)
    assert result.corrected_anchors[0].anchor_status == "exact"
    assert result.corrected_anchors[0].corrected_line_ids == ["P1L001", "P1L002"]


def test_invalid_marker_and_empty_line_ids_retry():
    doc = _doc(["1. 已知函数f(x)=2x+1"])
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="1",
                question_type="short_answer",
                stem_line_ids=[],
                stem_start_marker="不存在的标记",
                stem_end_marker=None,
                options_line_ids={},
            )
        ],
    )

    result = correct_anchors(annotation, doc)
    assert result.corrected_anchors[0].anchor_status == "retry"


def test_marker_in_answer_section_is_rejected():
    doc = _doc(
        [
            "1. 已知函数f(x)=2x+1",
            "参考答案",
            "1. B",
        ]
    )
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="1",
                question_type="single_choice",
                stem_line_ids=[],
                stem_start_marker="1. B",
                stem_end_marker=None,
                options_line_ids={},
            )
        ],
    )

    result = correct_anchors(annotation, doc)
    assert result.corrected_anchors[0].anchor_status == "retry"


def test_normalize_marker_unifies_full_width_punctuation():
    assert normalize_marker_text("3．如图所示（a）") == normalize_marker_text(
        "3.如图所示(a)"
    )


def test_short_marker_does_not_cross_match_to_another_question():
    doc = _doc(
        [
            "1. 已知函数f(x)=2x+1",
            "2. 已知函数f(x)=3x+2",
        ]
    )
    match = find_marker(
        "已知函数",
        doc.lines,
        question_number="2",
    )
    assert match is not None
    assert match.line_id == "P1L002"


def test_marker_with_wrong_question_number_is_rejected():
    doc = _doc(["1. 已知函数f(x)=2x+1"])
    match = find_marker(
        "1. 已知函数",
        doc.lines,
        question_number="2",
    )
    assert match is None


def test_similar_stems_do_not_cross_match():
    """两个相似题干不会跨题匹配。"""
    doc = _doc(
        [
            "1. 已知函数f(x)=2x+1",
            "则f(3)=",
            "A. 5",
            "B. 6",
            "2. 已知函数f(x)=3x+2",
            "则f(4)=",
            "A. 10",
            "B. 11",
        ]
    )
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="1",
                question_type="single_choice",
                stem_line_ids=[],
                stem_start_marker="1. 已知函数f(x)=2x+1",
                stem_end_marker="则f(3)=",
                options_line_ids={},
            ),
            L2QuestionAnnotation(
                question_number="2",
                question_type="single_choice",
                stem_line_ids=[],
                stem_start_marker="2. 已知函数f(x)=3x+2",
                stem_end_marker="则f(4)=",
                options_line_ids={},
            ),
        ],
    )

    result = correct_anchors(annotation, doc)
    assert result.corrected_anchors[0].corrected_line_ids == ["P1L001", "P1L002"]
    assert result.corrected_anchors[1].corrected_line_ids == ["P1L005", "P1L006"]


def test_split_question_number_line_is_expanded():
    """PP 把题号和题干拆到两行时，语义锚点应包含题号行。"""
    doc = _doc(
        [
            "3.",
            "2025年9月3日9时15分，阅兵仪式开始。下列说法正确的是（）",
            "A. 正确",
            "B. 错误",
        ]
    )
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="3",
                question_type="single_choice",
                stem_line_ids=[],
                stem_start_marker="2025年9月3日9时15分，阅兵仪式开始。下列说法正确的是（）",
                stem_end_marker="下列说法正确的是（）",
                options_line_ids={},
            )
        ],
    )

    result = correct_anchors(annotation, doc)
    assert result.corrected_anchors[0].anchor_status == "semantic"
    assert result.corrected_anchors[0].corrected_line_ids == ["P1L001", "P1L002"]
    assert "start_expanded_to=P1L001" in (result.corrected_anchors[0].evidence or "")


def test_choice_stem_ends_at_first_option_even_when_end_marker_is_early():
    """选择题 stem 以第一个选项前一行为准，即使 end_marker 落在题干首行。

    场景：LLM 的 end_marker 命中题干首行（P1L001），但选项从 P1L005 开始。
    期望：stem = P1L001-P1L004，不是只有 P1L001。
    """
    doc = _doc(
        [
            "7. 关于中国四个直辖市的发展",
            "问题背景描述第一行",
            "问题背景描述第二行",
            "问题背景描述第三行",
            "A. 北京",
            "B. 上海",
            "C. 天津",
            "D. 重庆",
        ]
    )
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="7",
                question_type="single_choice",
                stem_line_ids=[],
                stem_start_marker="7. 关于中国四个直辖市的发展",
                stem_end_marker="7. 关于中国四个直辖市的发展",
                options_line_ids={},
            )
        ],
    )

    result = correct_anchors(annotation, doc)
    assert result.corrected_anchors[0].anchor_status == "semantic"
    # stem should be P1L001-P1L004 (before first option at P1L005)
    assert result.corrected_anchors[0].corrected_line_ids == [
        "P1L001", "P1L002", "P1L003", "P1L004"
    ]
    assert "end=first_option_boundary" in (result.corrected_anchors[0].evidence or "")


def test_fill_in_stem_ends_at_next_question_boundary():
    doc = _doc(
        [
            "1. 第一行题干",
            "第二行题干",
            "2. 下一题",
        ]
    )
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="1",
                question_type="fill_in",
                stem_line_ids=["P1L001"],
                stem_start_marker="1. 第一行题干",
                stem_end_marker="第二行题干",
                options_line_ids={},
            )
        ],
    )

    result = correct_anchors(annotation, doc)
    assert result.corrected_anchors[0].corrected_line_ids == [
        "P1L001", "P1L002"
    ]


def test_composite_shared_material_uses_deterministic_stem_boundary():
    doc = _doc(
        [
            "A full scholarship covers almost everything.",
            "The competition is fierce.",
            "Follow these steps to apply.",
            "31. What can we learn from the passage?",
            "A. one",
            "B. two",
            "C. three",
            "D. four",
            "32. next question",
        ]
    )
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="31",
                question_type="single_choice",
                is_composite=True,
                stem_line_ids=["P1L001", "P1L004", "P1L008"],
                shared_material_line_ids=["P1L001", "P1L002", "P1L003"],
                stem_start_marker=None,
                stem_end_marker=None,
                options_line_ids={
                    "A": ["P1L005"],
                    "B": ["P1L006"],
                    "C": ["P1L007"],
                    "D": ["P1L008"],
                },
            )
        ],
    )

    result = correct_anchors(annotation, doc)
    # 展示契约 v0.5: 综合题容器保留 line_annotator 扩展的 stem_line_ids，
    # 不使用 anchor_corrector 的结果（shared_material 由展示层单独渲染）
    assert result.corrected_anchors[0].corrected_line_ids == [
        "P1L001", "P1L004", "P1L008"
    ]
    assert "composite_deterministic" in (
        result.corrected_anchors[0].evidence or ""
    )


def test_short_answer_stem_ends_at_next_question():
    """short_answer stem 以下一题题号行为准，确保确定性。

    场景：物理 Q15 跨页，LLM end_marker 一次在 P5L016，一次在 P6L005。
    期望：stem 都收敛到 Q16 题号行前一行。
    """
    doc = _doc(
        [
            "15. 验证牛顿第二定律的实验装置",
            "实验条件描述第一行",
            "实验条件描述第二行",
            "图注：滑轮细线小车",
            "16. 下一题的题干",
        ]
    )
    # run1: end_marker 在中间
    annotation1 = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="15",
                question_type="short_answer",
                stem_line_ids=[],
                stem_start_marker="15. 验证牛顿第二定律的实验装置",
                stem_end_marker="实验条件描述第二行",
                options_line_ids={},
            ),
            L2QuestionAnnotation(
                question_number="16",
                question_type="short_answer",
                stem_line_ids=[],
                stem_start_marker="16. 下一题的题干",
                stem_end_marker=None,
                options_line_ids={},
            ),
        ],
    )
    # run2: end_marker 更远
    annotation2 = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="15",
                question_type="short_answer",
                stem_line_ids=[],
                stem_start_marker="15. 验证牛顿第二定律的实验装置",
                stem_end_marker="图注：滑轮细线小车",
                options_line_ids={},
            ),
            L2QuestionAnnotation(
                question_number="16",
                question_type="short_answer",
                stem_line_ids=[],
                stem_start_marker="16. 下一题的题干",
                stem_end_marker=None,
                options_line_ids={},
            ),
        ],
    )

    result1 = correct_anchors(annotation1, doc)
    result2 = correct_anchors(annotation2, doc)

    # 两轮 stem 必须一致（由 next_question 边界决定）
    assert result1.questions[0].stem_line_ids == result2.questions[0].stem_line_ids
    # stem 应包含 Q15 到 Q16 之间的所有行
    assert "P1L004" in result1.questions[0].stem_line_ids  # 图注行
    assert "end=next_question_boundary" in (result1.corrected_anchors[0].evidence or "")


def test_composite_fill_in_stem_respects_end_marker():
    """综合题（语法填空型）end_marker 早于 next_q 时以 end_marker 截断。

    场景：语法填空 A/B/C 的材料挤在同一页，子题号行内编号（11(it)、14a），
    next_q 会越过整个 section 簇落到下一节题号行。LLM end_marker 指向
    section 内材料末尾，是更可靠的边界（2026-08-25 英语位置修复）。
    """
    doc = _doc(
        [
            "Tangshan started to revive 11(it) and rebuild for a brighter future.",
            "B",
            "Anger is an emotion 14a classmate borrows our things.",
            "C",
            "The IOC announced that Lang Ping 18(award) the award.",
            "21. 选词填空第一题",
        ]
    )
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="11",
                question_type="fill_in",
                is_composite=True,
                shared_material_line_ids=["P1L001"],
                stem_line_ids=["P1L001", "P1L002", "P1L003", "P1L004", "P1L005"],
                stem_start_marker="Tangshan started to revive",
                stem_end_marker="rebuild for a brighter future.",
                options_line_ids={},
            ),
        ],
    )

    result = correct_anchors(annotation, doc)
    # 展示契约 v0.5: 综合题容器保留 line_annotator 扩展的 stem_line_ids，
    # 不使用 anchor_corrector 的结果（end_marker 截断不再应用于综合题）
    assert result.questions[0].stem_line_ids == [
        "P1L001", "P1L002", "P1L003", "P1L004", "P1L005"
    ]


def test_truncation_uses_document_order_not_number_order():
    """截断边界按文档顺序取下一题号行，不按题号大小。

    场景：OCR/版面噪声题号行（如书面表达第一节标题拆行的 "48、49"）在
    文档顺序上早于当前题，但题号更大。旧逻辑按题号取 next 会把 stem 截空
    （英语 Q46 作文被误丢）；必须只考虑当前题干起点之后的行。
    """
    doc = _doc(
        [
            "48. 书面表达第一节的题",   # P1L001 题号 48，文档顺序在 46 之前
            "46. 作文题题干：给Jim写信",  # P1L002
            "注意：词数100左右",          # P1L003
            "参考答案",                   # P1L004 答案区起点
        ]
    )
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="46",
                question_type="short_answer",
                stem_line_ids=["P1L002", "P1L003"],
                stem_start_marker=None,
                stem_end_marker=None,
                options_line_ids={},
            ),
        ],
    )

    result = correct_anchors(annotation, doc)
    # stem 不被题号 48 的行截空
    assert result.questions[0].stem_line_ids == ["P1L002", "P1L003"]

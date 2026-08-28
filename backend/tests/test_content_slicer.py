"""内容切片器单元测试。"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

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


def test_merge_question_group_preserves_structure_signature():
    """共享材料题合并后保留 structure_signature，不再丢弃。"""
    from app.domains.document.content_slicer import _merge_question_group
    from app.domains.document.schemas_l2 import CorrectedAnchor, SlicedQuestion

    doc = _make_doc()
    line_by_id = {line.line_id: line for line in doc.lines}
    sig = {
        "object": "函数",
        "task": "求值",
        "method": "代入法",
        "condition": "f(x)=2x+1",
    }
    q1 = SlicedQuestion(
        question_number="1",
        question_type="fill_in",
        shared_material_line_ids=["P1L001"],
        stem_anchor=CorrectedAnchor(
            field="stem",
            llm_line_ids=[],
            corrected_line_ids=["P1L001"],
            anchor_status="exact",
        ),
        structure_signature=sig,
        confidence=0.9,
    )
    q2 = SlicedQuestion(
        question_number="2",
        question_type="fill_in",
        shared_material_line_ids=["P1L001"],
        stem_anchor=CorrectedAnchor(
            field="stem",
            llm_line_ids=[],
            corrected_line_ids=["P1L002"],
            anchor_status="exact",
        ),
        confidence=0.8,
    )

    merged = _merge_question_group([q1, q2], line_by_id)

    assert merged.structure_signature == sig


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


def test_slice_preserves_composite_metadata():
    """切片保留 LLM 标记的综合题 is_composite / sub_questions（防回归）。"""
    from app.domains.document.schemas_l2 import L2SubQuestion

    doc = _make_doc()
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="1",
                question_type="cloze",
                stem_line_ids=["P1L001"],
                options_line_ids={},
                is_composite=True,
                sub_questions=[
                    L2SubQuestion(qno="1", question_type="single_choice", answer="A", score=1.5),
                    L2SubQuestion(qno="2", question_type="single_choice", answer="B", score=1.5),
                ],
                shared_material_line_ids=["P1L001"],
            )
        ],
    )

    result = slice_questions(annotation, doc)
    assert len(result) == 1
    assert result[0].is_composite is True
    assert result[0].sub_questions is not None
    assert [sq.qno for sq in result[0].sub_questions] == ["1", "2"]
    assert result[0].sub_questions[0].answer == "A"


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


def test_section_validation_single_choice_no_section():
    """普通单选无 section_id 不应被标记。"""
    doc = _make_doc()
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="1",
                question_type="single_choice",
                stem_line_ids=["P1L001"],
                options_line_ids={"A": ["P1L002"]},
            ),
            L2QuestionAnnotation(
                question_number="2",
                question_type="single_choice",
                stem_line_ids=["P1L006"],
                options_line_ids={"A": ["P1L007"]},
            ),
        ],
    )

    result = slice_questions(annotation, doc)
    assert len(result) == 2
    assert result[0].section_id is None
    assert result[1].section_id is None


def test_section_validation_shared_material():
    """共享材料题 section_id 一致性验证。"""
    doc = _make_doc()
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="1",
                question_type="single_choice",
                section_id="cloze_1",
                stem_line_ids=["P1L001", "P1L002"],
                options_line_ids={"A": ["P1L003"]},
            ),
            L2QuestionAnnotation(
                question_number="2",
                question_type="single_choice",
                section_id="cloze_1",
                stem_line_ids=["P1L001", "P1L002"],  # 共享相同 stem
                options_line_ids={"A": ["P1L004"]},
            ),
        ],
    )

    result = slice_questions(annotation, doc)
    assert len(result) == 2
    assert result[0].section_id == "cloze_1"
    assert result[1].section_id == "cloze_1"


def test_section_validation_non_contiguous():
    """题号不连续的 section 应记录警告。"""
    doc = _make_doc()
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="1",
                question_type="single_choice",
                section_id="reading_1",
                stem_line_ids=["P1L001"],
                options_line_ids={"A": ["P1L002"]},
            ),
            L2QuestionAnnotation(
                question_number="3",  # 跳过 2
                question_type="single_choice",
                section_id="reading_1",
                stem_line_ids=["P1L006"],
                options_line_ids={"A": ["P1L007"]},
            ),
        ],
    )

    result = slice_questions(annotation, doc)
    assert len(result) == 2
    # 题号不连续应记录警告，但不影响切片结果
    assert result[0].section_id == "reading_1"
    assert result[1].section_id == "reading_1"


# ═══════════════════════════════════════════════════════════════════
# C4: 共享材料必须走 LLM 标注字段
# ═══════════════════════════════════════════════════════════════════


def _make_reading_doc() -> L1Document:
    """构造阅读理解测试文档。"""
    lines = [
        L1Line("P1L001", 1, 1, 1, "阅读下面的文章，回答问题。", "text"),
        L1Line("P1L002", 1, 2, 2, "文章内容第一段。", "text"),
        L1Line("P1L003", 1, 3, 3, "文章内容第二段。", "text"),
        L1Line("P1L004", 1, 4, 4, "1. 下列关于文章的理解，正确的是", "text"),
        L1Line("P1L005", 1, 5, 5, "（A）选项A", "text"),
        L1Line("P1L006", 1, 6, 6, "（B）选项B", "text"),
        L1Line("P1L007", 1, 7, 7, "2. 文章的主旨是", "text"),
        L1Line("P1L008", 1, 8, 8, "（A）选项A", "text"),
        L1Line("P1L009", 1, 9, 9, "（B）选项B", "text"),
    ]
    return L1Document(
        filename="reading.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source="native",
        total_pages=1,
    )


def test_line_annotator_parses_shared_material_line_ids():
    """line_annotator 从 LLM JSON 解析 shared_material_line_ids 并校验。"""
    from app.domains.document.line_annotator import annotate_document

    doc = _make_reading_doc()
    valid_line_ids = {l.line_id for l in doc.lines}

    mock_llm_response = '''
    {
        "filename": "reading.pdf",
        "questions": [
            {
                "question_number": "1",
                "question_type": "single_choice",
                "section_id": "reading_1",
                "stem_line_ids": ["P1L004"],
                "options_line_ids": {"A": ["P1L005"], "B": ["P1L006"]},
                "shared_material_line_ids": ["P1L002", "P1L003"]
            },
            {
                "question_number": "2",
                "question_type": "single_choice",
                "section_id": "reading_1",
                "stem_line_ids": ["P1L007"],
                "options_line_ids": {"A": ["P1L008"], "B": ["P1L009"]},
                "shared_material_line_ids": ["P1L002", "P1L003"]
            }
        ]
    }
    '''

    mock_gateway = AsyncMock()
    mock_gateway.complete = AsyncMock(return_value=mock_llm_response)

    import asyncio
    annotation = asyncio.run(annotate_document(doc, mock_gateway))

    assert len(annotation.questions) == 2
    q1 = annotation.questions[0]
    q2 = annotation.questions[1]
    assert q1.shared_material_line_ids == ["P1L002", "P1L003"]
    assert q2.shared_material_line_ids == ["P1L002", "P1L003"]


def test_line_annotator_filters_invalid_shared_material_line_ids():
    """line_annotator 过滤无效的 shared_material_line_ids。"""
    from app.domains.document.line_annotator import annotate_document

    doc = _make_reading_doc()

    mock_llm_response = '''
    {
        "filename": "reading.pdf",
        "questions": [
            {
                "question_number": "1",
                "question_type": "single_choice",
                "section_id": "reading_1",
                "stem_line_ids": ["P1L004"],
                "options_line_ids": {"A": ["P1L005"]},
                "shared_material_line_ids": ["P1L002", "P99L999"]
            }
        ]
    }
    '''

    mock_gateway = AsyncMock()
    mock_gateway.complete = AsyncMock(return_value=mock_llm_response)

    import asyncio
    annotation = asyncio.run(annotate_document(doc, mock_gateway))

    q1 = annotation.questions[0]
    # P99L999 不存在于 L1 文档，应被过滤
    assert q1.shared_material_line_ids == ["P1L002"]


def test_reading_comprehension_full_chain_consistent_no_issue():
    """阅读理解全链路：LLM 标记 is_composite=True 的题合并为综合题。"""
    doc = _make_reading_doc()
    annotation = L2DocumentAnnotation(
        filename="reading.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="1",
                question_type="single_choice",
                section_id="reading_1",
                stem_line_ids=["P1L004"],
                options_line_ids={"A": ["P1L005"], "B": ["P1L006"]},
                shared_material_line_ids=["P1L002", "P1L003"],
                is_composite=True,
            ),
            L2QuestionAnnotation(
                question_number="2",
                question_type="single_choice",
                section_id="reading_1",
                stem_line_ids=["P1L007"],
                options_line_ids={"A": ["P1L008"], "B": ["P1L009"]},
                shared_material_line_ids=["P1L002", "P1L003"],
                is_composite=True,
            ),
        ],
    )

    result = slice_questions(annotation, doc)
    # 两道都标记为 composite → 各自保留为独立的综合题（代码不强制合并 LLM 标记的题）
    assert len(result) == 2
    assert result[0].is_composite is True
    assert result[1].is_composite is True


def test_section_missing_shared_material_lines_flagged():
    """section 边界由 LLM 负责，缺失 shared_material_line_ids 不按关键词告警。"""
    doc = _make_reading_doc()
    annotation = L2DocumentAnnotation(
        filename="reading.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="1",
                question_type="single_choice",
                section_id="reading_1",
                stem_line_ids=["P1L004"],
                options_line_ids={"A": ["P1L005"]},
                shared_material_line_ids=[],  # 缺失
            ),
            L2QuestionAnnotation(
                question_number="2",
                question_type="single_choice",
                section_id="reading_1",
                stem_line_ids=["P1L007"],
                options_line_ids={"A": ["P1L008"]},
                shared_material_line_ids=[],  # 缺失
            ),
        ],
    )

    result = slice_questions(annotation, doc)
    assert len(result) == 2
    assert not any("共享材料" in i for i in result[0].issues)
    assert not any("共享材料" in i for i in result[1].issues)


def test_section_inconsistent_shared_material_lines_flagged():
    """同一 section 的 shared_material_line_ids 不一致但有重叠 → 不强制合并（尊重 LLM 判断）。"""
    doc = _make_reading_doc()
    annotation = L2DocumentAnnotation(
        filename="reading.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="1",
                question_type="single_choice",
                section_id="reading_1",
                stem_line_ids=["P1L004"],
                options_line_ids={"A": ["P1L005"]},
                shared_material_line_ids=["P1L002", "P1L003"],
            ),
            L2QuestionAnnotation(
                question_number="2",
                question_type="single_choice",
                section_id="reading_1",
                stem_line_ids=["P1L007"],
                options_line_ids={"A": ["P1L008"]},
                shared_material_line_ids=["P1L002"],  # 不一致：少了 P1L003
            ),
        ],
    )

    result = slice_questions(annotation, doc)
    # LLM 未标记 is_composite → 保留为独立题（代码不强制合并）
    assert len(result) == 2
    assert result[0].is_composite is False
    assert result[1].is_composite is False


def test_pipeline_result_to_dict_includes_shared_material_line_ids():
    """PipelineResult.to_dict() 输出 shared_material_line_ids。"""
    from app.domains.document.pipeline import PipelineResult
    from app.domains.document.schemas_l2 import SlicedQuestion

    r = PipelineResult()
    sq = SlicedQuestion(
        question_number="1",
        question_type="single_choice",
        stem="测试题干",
        shared_material_line_ids=["P1L002", "P1L003"],
    )
    r.sliced_questions = [sq]

    d = r.to_dict()
    assert len(d["questions"]) == 1
    assert d["questions"][0]["shared_material_line_ids"] == ["P1L002", "P1L003"]


# ═══════════════════════════════════════════════════════════════════
# Fix 6: LLM Prompt 行号格式
# ═══════════════════════════════════════════════════════════════════


def test_build_annotation_prompt_contains_real_line_format():
    """build_annotation_prompt 输出实际行号格式（如 P1L001），不输出占位符。"""
    from app.domains.document.line_annotator import build_annotation_prompt

    doc = _make_reading_doc()
    prompt = build_annotation_prompt(doc)

    # 包含实际行号示例
    assert "P1L001" in prompt
    # 不包含格式占位符
    assert "P{page}" not in prompt
    assert "P{{page}}" not in prompt


# ═══════════════════════════════════════════════════════════════════
# Fix 7: C4 全链路测试（annotate → slice）
# ═══════════════════════════════════════════════════════════════════


def test_shared_material_full_chain_consistent_no_issue():
    """全链路：一致的 shared_material_line_ids → sq.issues 无共享材料警告。"""
    import asyncio
    from app.domains.document.line_annotator import annotate_document
    from app.domains.document.content_slicer import slice_questions

    doc = _make_reading_doc()

    mock_llm_response = '''
    {
        "filename": "reading.pdf",
        "questions": [
            {
                "question_number": "1",
                "question_type": "single_choice",
                "section_id": "reading_1",
                "stem_line_ids": ["P1L004"],
                "options_line_ids": {"A": ["P1L005"], "B": ["P1L006"]},
                "shared_material_line_ids": ["P1L002", "P1L003"],
                "is_composite": true
            },
            {
                "question_number": "2",
                "question_type": "single_choice",
                "section_id": "reading_1",
                "stem_line_ids": ["P1L007"],
                "options_line_ids": {"A": ["P1L008"], "B": ["P1L009"]},
                "shared_material_line_ids": ["P1L002", "P1L003"],
                "is_composite": true
            }
        ]
    }
    '''

    mock_gateway = AsyncMock()
    mock_gateway.complete = AsyncMock(return_value=mock_llm_response)

    annotation = asyncio.run(annotate_document(doc, mock_gateway))
    result = slice_questions(annotation, doc)

    # LLM 标记 is_composite=True → 各自保留为综合题（代码不强制合并）
    assert len(result) == 2
    assert result[0].is_composite is True
    assert result[1].is_composite is True


def test_shared_material_full_chain_missing_not_flagged():
    """全链路：缺失 shared_material_line_ids 不再由 section 规则告警。"""
    import asyncio
    from app.domains.document.line_annotator import annotate_document
    from app.domains.document.content_slicer import slice_questions

    doc = _make_reading_doc()

    mock_llm_response = '''
    {
        "filename": "reading.pdf",
        "questions": [
            {
                "question_number": "1",
                "question_type": "single_choice",
                "section_id": "reading_1",
                "stem_line_ids": ["P1L004"],
                "options_line_ids": {"A": ["P1L005"]},
                "shared_material_line_ids": []
            },
            {
                "question_number": "2",
                "question_type": "single_choice",
                "section_id": "reading_1",
                "stem_line_ids": ["P1L007"],
                "options_line_ids": {"A": ["P1L008"]},
                "shared_material_line_ids": []
            }
        ]
    }
    '''

    mock_gateway = AsyncMock()
    mock_gateway.complete = AsyncMock(return_value=mock_llm_response)

    annotation = asyncio.run(annotate_document(doc, mock_gateway))
    result = slice_questions(annotation, doc)

    assert len(result) == 2
    assert not any("缺少" in i or "shared_material" in i for i in result[0].issues)
    assert not any("缺少" in i or "shared_material" in i for i in result[1].issues)


def test_shared_material_full_chain_inconsistent_not_flagged():
    """全链路：shared_material_line_ids 不一致不再由 section 规则告警。"""
    import asyncio
    from app.domains.document.line_annotator import annotate_document
    from app.domains.document.content_slicer import slice_questions

    doc = _make_reading_doc()

    mock_llm_response = '''
    {
        "filename": "reading.pdf",
        "questions": [
            {
                "question_number": "1",
                "question_type": "single_choice",
                "section_id": "reading_1",
                "stem_line_ids": ["P1L004"],
                "options_line_ids": {"A": ["P1L005"]},
                "shared_material_line_ids": ["P1L002", "P1L003"]
            },
            {
                "question_number": "2",
                "question_type": "single_choice",
                "section_id": "reading_1",
                "stem_line_ids": ["P1L007"],
                "options_line_ids": {"A": ["P1L008"]},
                "shared_material_line_ids": ["P1L002"]
            }
        ]
    }
    '''

    mock_gateway = AsyncMock()
    mock_gateway.complete = AsyncMock(return_value=mock_llm_response)

    annotation = asyncio.run(annotate_document(doc, mock_gateway))
    result = slice_questions(annotation, doc)

    # LLM 未标记 is_composite → 保留为独立题（代码不强制合并）
    assert len(result) == 2
    assert result[0].is_composite is False
    assert result[1].is_composite is False


def test_shared_material_full_chain_invalid_ids_filtered():
    """全链路：含无效 ID 的 shared_material_line_ids → 无效 ID 被过滤。"""
    import asyncio
    from app.domains.document.line_annotator import annotate_document
    from app.domains.document.content_slicer import slice_questions

    doc = _make_reading_doc()

    mock_llm_response = '''
    {
        "filename": "reading.pdf",
        "questions": [
            {
                "question_number": "1",
                "question_type": "single_choice",
                "section_id": "reading_1",
                "stem_line_ids": ["P1L004"],
                "options_line_ids": {"A": ["P1L005"]},
                "shared_material_line_ids": ["P1L002", "P99L999"]
            }
        ]
    }
    '''

    mock_gateway = AsyncMock()
    mock_gateway.complete = AsyncMock(return_value=mock_llm_response)

    annotation = asyncio.run(annotate_document(doc, mock_gateway))
    result = slice_questions(annotation, doc)

    assert len(result) == 1
    # P99L999 被过滤，只剩 P1L002
    assert result[0].shared_material_line_ids == ["P1L002"]


# ═══════════════════════════════════════════════════════════════════
# Fix 9: PipelineResult.to_dict() 图片元数据
# ═══════════════════════════════════════════════════════════════════


def test_pipeline_result_to_dict_images_include_url_and_xref():
    """PipelineResult.to_dict() 输出图片的 url 和 xref 字段。"""
    from app.domains.document.pipeline import PipelineResult
    from app.domains.document.schemas_l1 import L1Document, L1Image, L1Page

    r = PipelineResult()
    r.l1_document = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=[])],
        lines=[],
        images=[
            L1Image(
                image_id="P1IMG001",
                page_no=1,
                bbox={"x1": 10, "y1": 20, "x2": 100, "y2": 80},
                xref=42,
                source="ppsv3",
                url="https://example.com/img.png",
                placement="stem",
            )
        ],
        source="ppsv3",
        total_pages=1,
    )

    d = r.to_dict()
    assert len(d["images"]) == 1
    img = d["images"][0]
    assert img["url"] == "https://example.com/img.png"
    assert img["xref"] == 42


def test_shared_material_not_required_for_ordinary_fill_in_section():
    """数学填空题/物理实验题不是共享材料题，缺失 shared_material 不应误报。"""
    from app.domains.document.content_slicer import _validate_shared_material_sections
    from app.domains.document.schemas_l2 import SlicedQuestion

    sq1 = SlicedQuestion(
        question_number="11",
        question_type="fill_in",
        section_id="填空题",
    )
    sq2 = SlicedQuestion(
        question_number="12",
        question_type="fill_in",
        section_id="填空题",
    )

    _validate_shared_material_sections([sq1, sq2])

    assert not any("shared_material" in i or "共享材料" in i for i in sq1.issues)
    assert not any("shared_material" in i or "共享材料" in i for i in sq2.issues)


# ═══════════════════════════════════════════════════════════════════
# P4E.1：行内选项拆分 + 子题切片文本（2026-08-27，V1_LESSONS 3.21）
# 背景：完形 10 个子题的 A 被拼成一个 A；子题内容链路丢失（LOG v6.43）。
# ═══════════════════════════════════════════════════════════════════


def test_inline_split_compact_options():
    """`A.xxxB.yyyC.zzzD.www` 单行紧凑选项拆为独立选项。"""
    from app.domains.document.content_slicer import _inline_split_options

    parts = _inline_split_options("A.充分不必要条件B.必要不充分条件C.充要条件D.既不充分也不必要条件")
    assert parts == [
        ("A", "充分不必要条件"),
        ("B", "必要不充分条件"),
        ("C", "充要条件"),
        ("D", "既不充分也不必要条件"),
    ]


def test_inline_split_leading_segment_inferred_as_a():
    """首段无 label 时推断为 A（`①②③ | B. ①②③ | C. ①②③ | D. ①②③④`）。"""
    from app.domains.document.content_slicer import _inline_split_options

    parts = _inline_split_options("①②③ | B. ①②③ | C. ①②③ | D. ①②③④")
    assert parts == [
        ("A", "①②③ |"),
        ("B", "①②③ |"),
        ("C", "①②③ |"),
        ("D", "①②③④"),
    ]


def test_inline_split_plain_line_returns_empty():
    """无多选项标记的普通行返回 []（整行归调用方 label）。"""
    from app.domains.document.content_slicer import _inline_split_options

    assert _inline_split_options("已知函数f(x)=2x+1") == []
    assert _inline_split_options("（A）5") == []


def test_slice_options_splits_inline_and_dedups_lines():
    """_slice_options：单行多选项拆分 + 行号去重。"""
    from app.domains.document.content_slicer import _slice_options

    doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=[])],
        lines=[
            L1Line("P1L001", 1, 1, 1, "A.甲B.乙C.丙D.丁", "text"),
            # LLM 为多选项重复输出同一行 → 去重后不重复
        ],
        source="native",
        total_pages=1,
    )
    line_by_id = {l.line_id: l for l in doc.lines}
    result = _slice_options(
        {"A": ["P1L001", "P1L001"], "B": ["P1L001"], "C": ["P1L001"], "D": ["P1L001"]},
        line_by_id,
    )
    assert result == [
        {"label": "A", "text": "甲"},
        {"label": "B", "text": "乙"},
        {"label": "C", "text": "丙"},
        {"label": "D", "text": "丁"},
    ]


def test_composite_sub_questions_sliced_with_text():
    """LLM 标记综合题的子题带行号时，切片出子题 stem/options 文本（P4E.1）。

    背景：LLM 输出完形 20 个子题各带 options_line_ids，此前 _slice_single_question
    只透传行号不切文本 → 入库子题只有 qno/answer/type（LOG v6.43 链路断裂 #1）。
    """
    from app.domains.document.schemas_l2 import L2SubQuestion

    lines = [
        L1Line("P1L001", 1, 1, 1, "1. 完形文章...", "text"),
        L1Line("P1L002", 1, 2, 2, "子题1题干", "text"),
        L1Line("P1L003", 1, 3, 3, "A.开心", "text"),
        L1Line("P1L004", 1, 4, 4, "B.难过", "text"),
        L1Line("P1L005", 1, 5, 5, "子题2题干", "text"),
        L1Line("P1L006", 1, 6, 6, "A.快", "text"),
        L1Line("P1L007", 1, 7, 7, "B.慢", "text"),
    ]
    doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source="native",
        total_pages=1,
    )

    # LLM 标记 is_composite=True 的综合题（生产主路径：_slice_single_question 透传）
    annotation = L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="1",
                question_type="single_choice",
                stem_line_ids=["P1L001"],
                options_line_ids={},
                is_composite=True,
                sub_questions=[
                    L2SubQuestion(
                        qno="1", question_type="single_choice", answer="A",
                        stem_line_ids=["P1L002"],
                        options_line_ids={"A": ["P1L003"], "B": ["P1L004"]},
                    ),
                    L2SubQuestion(
                        qno="2", question_type="single_choice", answer="B",
                        stem_line_ids=["P1L005"],
                        options_line_ids={"A": ["P1L006"], "B": ["P1L007"]},
                    ),
                ],
            )
        ],
    )

    result = slice_questions(annotation, doc)
    assert len(result) == 1
    comp = result[0]
    assert comp.is_composite
    assert comp.sub_questions is not None
    assert len(comp.sub_questions) == 2

    s1, s2 = comp.sub_questions
    # 子题切片文本（P4E.1 核心断言）
    assert "子题1题干" in s1.stem
    assert s1.options == [
        {"label": "A", "text": "开心"},
        {"label": "B", "text": "难过"},
    ]
    assert "子题2题干" in s2.stem
    assert s2.options == [
        {"label": "A", "text": "快"},
        {"label": "B", "text": "慢"},
    ]
    # 行号保留
    assert s1.options_line_ids == {"A": ["P1L003"], "B": ["P1L004"]}


# ═══════════════════════════════════════════════════════════════════
# P4E.1：填空位结构化标记（〔N〕入库，前端渲染高亮，2026-08-28）
# ═══════════════════════════════════════════════════════════════════


def test_mark_blank_positions_cloze_english():
    """完形（英语）：孤立数字 ∈ qno → 〔N〕；年份等普通数字不误标。"""
    from app.domains.document.content_slicer import _mark_blank_positions

    stem = "I sat in the dressing room before my first major 1, feeling anxious. was 2. In 2026, we try again."
    out = _mark_blank_positions(stem, ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"], "英语")
    assert "major 〔1〕" in out
    assert "was 〔2〕" in out
    assert "In 2026, we try again" in out  # 2026 不在 qno 集合 → 不替换


def test_mark_blank_positions_grammar_fill():
    """语法填空：{11} / （12） 显式标记 → 〔11〕〔12〕（所有科目）。"""
    from app.domains.document.content_slicer import _mark_blank_positions

    stem = "Tangshan started to revive {11} (it). The new city has become a home （12） more than seven million people."
    out = _mark_blank_positions(stem, ["11", "12", "13"], "英语")
    assert "revive 〔11〕 (it)" in out
    assert "home 〔12〕 more" in out


def test_mark_blank_positions_math_untouched():
    """数学（非文本科目）：孤立数字不替换（数字密集），下划线填空位原样保留。"""
    from app.domains.document.content_slicer import _mark_blank_positions

    stem = "AB=2AD=4，则2λ-μ=______．"
    out = _mark_blank_positions(stem, [], "数学")
    assert out == "AB=2AD=4，则2λ-μ=______．"


def test_mark_blank_positions_no_subject():
    """无学科信息时仅处理显式标记，孤立数字不替换。"""
    from app.domains.document.content_slicer import _mark_blank_positions

    stem = "major 1, was 2"
    out = _mark_blank_positions(stem, ["1", "2"], None)
    assert out == "major 1, was 2"


def test_mark_blank_positions_digit_followed_by_letter():
    """OCR 丢空格场景（数字后紧跟字母）：`my 5was` → `my 〔5〕was`。

    2026-08-28 修正：完形 `my 5was`/`don't 8mistakes` 数字后是字母，
    原正则排除字母导致漏标 → 现允许（仅文本科目启用）。
    """
    from app.domains.document.content_slicer import _mark_blank_positions

    stem = "Trusting my 5was the only thing. don't 8mistakes. I've 10it."
    out = _mark_blank_positions(stem, [str(i) for i in range(1, 11)], "英语")
    assert "my 〔5〕was" in out
    assert "don't 〔8〕mistakes" in out
    assert "I've 〔10〕it." in out

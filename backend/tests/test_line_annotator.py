"""LLM 行号标注器单元测试。"""

import json

import pytest

from app.ai.gateway import LLMGateway
from app.ai.providers import MockLLMProvider
from app.domains.document.line_annotator import (
    _canonical_question_type,
    _merge_wordbank_fill_composites,
    _split_no_material_fill_composites,
    annotate_document,
    build_annotation_prompt,
)
from app.domains.document.schemas_l2 import L2QuestionAnnotation, L2SubQuestion
from app.domains.document.schemas_l1 import L1Document, L1Line, L1Page


def _make_simple_doc() -> L1Document:
    """构造简单的测试 L1 文档。"""
    lines = [
        L1Line("P1L001", 1, 1, 1, "一、选择题", "text"),
        L1Line("P1L002", 1, 2, 2, "1. 已知函数f(x)=2x+1，则f(3)=", "text"),
        L1Line("P1L003", 1, 3, 3, "（A）5", "text"),
        L1Line("P1L004", 1, 4, 4, "（B）6", "text"),
        L1Line("P1L005", 1, 5, 5, "（C）7", "text"),
        L1Line("P1L006", 1, 6, 6, "（D）8", "text"),
        L1Line("P1L007", 1, 7, 7, "2. 计算：√4 + √9 =", "text"),
        L1Line("P1L008", 1, 8, 8, "（A）3", "text"),
        L1Line("P1L009", 1, 9, 9, "（B）4", "text"),
        L1Line("P1L010", 1, 10, 10, "（C）5", "text"),
        L1Line("P1L011", 1, 11, 11, "（D）6", "text"),
    ]
    return L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source="native",
        total_pages=1,
    )


def _mock_llm_response() -> str:
    """构造 mock LLM 响应。"""
    return json.dumps({
        "filename": "test.pdf",
        "subject": "数学",
        "questions": [
            {
                "question_number": "1",
                "question_type": "single_choice",
                "section_id": "选择题",
                "stem_line_ids": ["P1L002"],
                "options_line_ids": {
                    "A": ["P1L003"],
                    "B": ["P1L004"],
                    "C": ["P1L005"],
                    "D": ["P1L006"],
                },
                "difficulty": 1,
                "score": 5.0,
                "knowledge_points": ["函数求值"],
            },
            {
                "question_number": "2",
                "question_type": "single_choice",
                "section_id": "选择题",
                "stem_line_ids": ["P1L007"],
                "options_line_ids": {
                    "A": ["P1L008"],
                    "B": ["P1L009"],
                    "C": ["P1L010"],
                    "D": ["P1L011"],
                },
                "difficulty": 1,
                "score": 5.0,
                "knowledge_points": ["根式运算"],
            },
        ],
        "metadata_confidence": 0.9,
        "warnings": [],
    })


def test_build_annotation_prompt_contains_line_ids():
    """Prompt 包含行号引用。"""
    doc = _make_simple_doc()
    prompt = build_annotation_prompt(doc)
    assert "P1L001" in prompt
    assert "P1L011" in prompt
    assert "1. 已知函数f(x)=2x+1" in prompt
    assert "single_choice / multiple_choice / fill_in / true_false / short_answer" in prompt
    assert "answer_line_ids" in prompt
    assert "explanation_line_ids" in prompt
    assert "stem_markers" in prompt


def test_annotation_prompt_uses_semantic_grouping_not_hardcoded_ranges():
    doc = _make_simple_doc()
    prompt = build_annotation_prompt(doc)
    assert "多个小题只有在共享同一篇材料/文章/短文时才合并为综合题" in prompt
    assert "不得仅因为题型相同或题号连续就合并" in prompt
    assert "10 个带题号的句子" not in prompt


def test_build_annotation_prompt_includes_retry_hints():
    """retry hints 必须追加到第二遍 LLM prompt 中。"""
    doc = _make_simple_doc()
    prompt = build_annotation_prompt(
        doc,
        retry_hints=["题目 1：所有选项行号缺失，请重新输出 options_line_ids"],
    )
    assert "上一轮标注问题" in prompt
    assert "题目 1：所有选项行号缺失" in prompt


def test_annotate_parses_answer_and_explanation_line_ids():
    """标注解析答案/详解行号引用，并过滤无效行号。"""
    doc = _make_simple_doc()
    response = json.dumps({
        "filename": "test.pdf",
        "subject": "数学",
        "questions": [
            {
                "question_number": "1",
                "question_type": "single_choice",
                "section_id": "选择题",
                "stem_line_ids": ["P1L002"],
                "options_line_ids": {
                    "A": ["P1L003"],
                    "B": ["P1L004"],
                    "C": ["P1L005"],
                    "D": ["P1L006"],
                },
                "answer": "A",
                "answer_line_ids": ["P1L003", "P1L999"],
                "explanation_line_ids": ["P1L002", "P1L998"],
            }
        ],
        "metadata_confidence": 0.9,
    })
    gateway = LLMGateway(
        mode="live",
        providers=[MockLLMProvider(response=response)],
    )

    import asyncio
    result = asyncio.run(annotate_document(doc, gateway))
    q = result.questions[0]
    assert q.answer == "A"
    assert q.answer_line_ids == ["P1L003"]
    assert q.explanation_line_ids == ["P1L002"]


def test_annotate_parses_stem_markers():
    """标注解析 stem_markers，并保留为语义锚点。"""
    doc = _make_simple_doc()
    response = json.dumps({
        "filename": "test.pdf",
        "questions": [
            {
                "question_number": "1",
                "question_type": "single_choice",
                "section_id": "选择题",
                "stem_markers": {
                    "start": "1. 已知函数f(x)=2x+1",
                    "end": "则f(3)=",
                },
                "stem_line_ids": ["P1L002"],
                "options_line_ids": {"A": ["P1L003"]},
            }
        ],
        "metadata_confidence": 0.9,
    })
    gateway = LLMGateway(
        mode="live",
        providers=[MockLLMProvider(response=response)],
    )

    import asyncio
    result = asyncio.run(annotate_document(doc, gateway))
    q = result.questions[0]
    assert q.stem_start_marker == "1. 已知函数f(x)=2x+1"
    assert q.stem_end_marker == "则f(3)="


def test_annotate_returns_l2_annotation():
    """标注返回 L2DocumentAnnotation。"""
    doc = _make_simple_doc()
    gateway = LLMGateway(
        mode="live",
        providers=[MockLLMProvider(response=_mock_llm_response())],
    )

    import asyncio
    result = asyncio.run(annotate_document(doc, gateway))

    assert result.filename == "test.pdf"
    assert result.subject == "数学"
    assert len(result.questions) == 2
    assert result.questions[0].question_number == "1"
    assert result.questions[0].question_type == "single_choice"
    assert result.questions[0].stem_line_ids == ["P1L002"]
    assert result.questions[0].options_line_ids["A"] == ["P1L003"]
    assert result.raw_response == _mock_llm_response()


def test_annotate_filters_invalid_line_ids():
    """标注过滤无效行 ID。"""
    doc = _make_simple_doc()

    response = json.dumps({
        "filename": "test.pdf",
        "questions": [
            {
                "question_number": "1",
                "question_type": "single_choice",
                "stem_line_ids": ["P1L002", "P1L999"],
                "options_line_ids": {
                    "A": ["P1L003"],
                    "B": ["P1L998"],
                },
            }
        ],
        "metadata_confidence": 0.5,
    })

    gateway = LLMGateway(
        mode="live",
        providers=[MockLLMProvider(response=response)],
    )

    import asyncio
    result = asyncio.run(annotate_document(doc, gateway))

    assert result.questions[0].stem_line_ids == ["P1L002"]
    assert result.questions[0].options_line_ids["A"] == ["P1L003"]
    assert result.questions[0].options_line_ids["B"] == []


def test_annotate_does_not_resolve_nearby_invalid_line_ids():
    """无效行号只过滤不吸附，由 LLM 重试链路修正。"""
    doc = _make_simple_doc()
    response = json.dumps({
        "filename": "test.pdf",
        "questions": [
            {
                "question_number": "1",
                "question_type": "single_choice",
                "stem_line_ids": ["P1L002"],
                "options_line_ids": {"A": ["P1L003"]},
                "answer": "B",
                "answer_line_ids": ["P1L012"],
            }
        ],
        "metadata_confidence": 0.5,
    })
    gateway = LLMGateway(
        mode="live",
        providers=[MockLLMProvider(response=response)],
    )

    import asyncio
    result = asyncio.run(annotate_document(doc, gateway))
    assert result.questions[0].answer_line_ids == []


def test_annotate_handles_fenced_json():
    """标注处理 markdown fence 包裹的 JSON。"""
    doc = _make_simple_doc()
    fenced_response = f"```json\n{_mock_llm_response()}\n```"
    gateway = LLMGateway(
        mode="live",
        providers=[MockLLMProvider(response=fenced_response)],
    )

    import asyncio
    result = asyncio.run(annotate_document(doc, gateway))
    assert len(result.questions) == 2


def test_annotate_normalizes_multi_subquestion_fill_in_to_short_answer():
    """fill_in 且题干含多个小问（（1）（2）...）→ short_answer（物理实验题边界）。"""
    doc = _make_simple_doc()
    # 额外构造带（1）（2）（3）小问的题干行
    extra_lines = [
        L1Line("P2L001", 2, 1, 12, "16． 某同学用如图装置做实验", "text"),
        L1Line("P2L002", 2, 2, 13, "（1）求加速度", "text"),
        L1Line("P2L003", 2, 3, 14, "（2）求质量", "text"),
        L1Line("P2L004", 2, 4, 15, "（3）求位移", "text"),
    ]
    doc = L1Document(
        filename="test.pdf",
        pages=list(doc.pages) + [L1Page(page_no=2, lines=extra_lines)],
        lines=doc.lines + extra_lines,
        source="native",
        total_pages=2,
    )
    response = json.dumps({
        "filename": "test.pdf",
        "subject": "物理",
        "questions": [
            {
                "question_number": "16",
                "question_type": "fill_in",
                "section_id": None,
                "stem_line_ids": ["P2L001", "P2L002", "P2L003", "P2L004"],
                "options_line_ids": {},
            }
        ],
        "metadata_confidence": 0.5,
    })
    gateway = LLMGateway(
        mode="live",
        providers=[MockLLMProvider(response=response)],
    )

    import asyncio
    result = asyncio.run(annotate_document(doc, gateway))
    assert result.questions[0].question_type == "short_answer", (
        f"多小问 fill_in 应归一化为 short_answer: {result.questions[0].question_type}"
    )


def test_annotate_keeps_single_subquestion_fill_in():
    """单个小问或无小问的 fill_in 保持 fill_in（数学填空不误伤）。"""
    doc = _make_simple_doc()
    response = json.dumps({
        "filename": "test.pdf",
        "subject": "数学",
        "questions": [
            {
                "question_number": "1",
                "question_type": "fill_in",
                "section_id": None,
                "stem_line_ids": ["P1L002"],
                "options_line_ids": {},
            }
        ],
        "metadata_confidence": 0.5,
    })
    gateway = LLMGateway(
        mode="live",
        providers=[MockLLMProvider(response=response)],
    )

    import asyncio
    result = asyncio.run(annotate_document(doc, gateway))
    assert result.questions[0].question_type == "fill_in"


def test_annotate_normalizes_subquestion_numbers_to_parent():
    """物理实验题/解答题被 LLM 拆成 15(1)/15(2)/16(1)... 时，应合并回母题号。"""
    doc = _make_simple_doc()
    response = json.dumps({
        "filename": "test.pdf",
        "subject": "物理",
        "questions": [
            {
                "question_number": "15(1)",
                "question_type": "fill_in",
                "section_id": "实验题_15",
                "stem_line_ids": ["P1L002"],
                "options_line_ids": {},
                "score": 2,
            },
            {
                "question_number": "15(2)",
                "question_type": "fill_in",
                "section_id": "实验题_15",
                "stem_line_ids": ["P1L003"],
                "options_line_ids": {},
                "score": 2,
            },
            {
                "question_number": "15(3)",
                "question_type": "fill_in",
                "section_id": "实验题_15",
                "stem_line_ids": ["P1L004"],
                "options_line_ids": {},
                "score": 4,
            },
            {
                "question_number": "16(1)",
                "question_type": "single_choice",
                "section_id": "实验题_16",
                "stem_line_ids": ["P1L005"],
                "options_line_ids": {"A": ["P1L006"]},
                "score": 2,
            },
            {
                "question_number": "16(2)",
                "question_type": "short_answer",
                "section_id": "实验题_16",
                "stem_line_ids": ["P1L007"],
                "options_line_ids": {},
                "score": 2,
            },
        ],
        "metadata_confidence": 0.5,
    })
    gateway = LLMGateway(
        mode="live",
        providers=[MockLLMProvider(response=response)],
    )

    import asyncio
    result = asyncio.run(annotate_document(doc, gateway))
    assert [q.question_number for q in result.questions] == ["15", "16"]

    q15 = result.questions[0]
    assert q15.question_type == "short_answer"
    assert q15.section_id == "实验题"
    assert q15.stem_line_ids == ["P1L002", "P1L003", "P1L004"]
    assert q15.options_line_ids == {}
    assert q15.score == 8

    q16 = result.questions[1]
    assert q16.question_type == "short_answer"
    assert q16.section_id == "实验题"
    assert q16.stem_line_ids == ["P1L005", "P1L007"]
    assert q16.options_line_ids == {}
    assert q16.score == 4


def test_annotate_single_subquestion_also_normalizes_to_parent():
    """即使某次 LLM 只输出一个子题，也归一化为母题号并统一为 short_answer。"""
    doc = _make_simple_doc()
    response = json.dumps({
        "filename": "test.pdf",
        "subject": "物理",
        "questions": [
            {
                "question_number": "16（1）",
                "question_type": "single_choice",
                "section_id": "实验题_16",
                "stem_line_ids": ["P1L002"],
                "options_line_ids": {"A": ["P1L003"]},
                "score": 2,
            }
        ],
        "metadata_confidence": 0.5,
    })
    gateway = LLMGateway(
        mode="live",
        providers=[MockLLMProvider(response=response)],
    )

    import asyncio
    result = asyncio.run(annotate_document(doc, gateway))
    assert [q.question_number for q in result.questions] == ["16"]
    assert result.questions[0].question_type == "short_answer"


def test_annotate_drops_group_placeholder_question_binding():
    """“（1）（集团校自创题）”占位题号不应把下一题题干绑成同一道题。"""
    lines = [
        L1Line("P1L001", 1, 1, 1, "（1）（集团校自创题）", "text"),
        L1Line(
            "P1L002", 1, 2, 2,
            "（2）下列函数中，在定义域内单调递减且值域为(0,+∞)的是",
            "text",
        ),
        L1Line("P1L003", 1, 3, 3, "（A）y=-x", "text"),
        L1Line("P1L004", 1, 4, 4, "（B）y=1/x", "text"),
    ]
    doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source="ppsv3",
        total_pages=1,
    )
    response = json.dumps({
        "filename": "test.pdf",
        "questions": [
            {
                "question_number": "1",
                "question_type": "single_choice",
                "section_id": "选择题",
                "stem_line_ids": ["P1L001", "P1L002"],
                "options_line_ids": {
                    "A": ["P1L003"],
                    "B": ["P1L004"],
                },
            }
        ],
        "metadata_confidence": 0.5,
    })
    gateway = LLMGateway(
        mode="live",
        providers=[MockLLMProvider(response=response)],
    )

    import asyncio
    result = asyncio.run(annotate_document(doc, gateway))

    assert len(result.questions) == 1
    assert result.questions[0].question_number == "2"
    assert "P1L001" not in result.questions[0].stem_line_ids
    assert result.questions[0].stem_line_ids == ["P1L002"]
    assert result.questions[0].options_line_ids == {
        "A": ["P1L003"],
        "B": ["P1L004"],
    }


def test_annotate_keeps_standalone_group_placeholder_with_answer():
    """“（1）（集团校自创题）”若在答案表中有本题答案，保留为待人工补题的真实题位。"""
    lines = [
        L1Line("P1L001", 1, 1, 1, "（1）（集团校自创题）", "text"),
        L1Line("P5L001", 5, 1, 2, "（1）A", "text"),
    ]
    doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source="ppsv3",
        total_pages=1,
    )
    response = json.dumps({
        "filename": "test.pdf",
        "questions": [
            {
                "question_number": "1",
                "question_type": "single_choice",
                "section_id": "选择题",
                "stem_line_ids": ["P1L001"],
                "options_line_ids": {},
                "answer": "A",
                "answer_line_ids": ["P5L001"],
            }
        ],
        "metadata_confidence": 0.5,
    })
    gateway = LLMGateway(
        mode="live",
        providers=[MockLLMProvider(response=response)],
    )

    import asyncio
    result = asyncio.run(annotate_document(doc, gateway))

    assert [q.question_number for q in result.questions] == ["1"]
    assert result.questions[0].stem_line_ids == ["P1L001"]
    assert result.questions[0].answer == "A"


def test_cloze_canonical_type_is_single_choice():
    assert _canonical_question_type("cloze") == "single_choice"


def test_split_no_material_fill_composites_preserves_shared_composites():
    q11 = L2QuestionAnnotation(
        question_number="11",
        question_type="fill_in",
        section_id="语法填空_1",
        shared_material_line_ids=[],
        stem_line_ids=["P2L005"],
        answer_line_ids=["P10L033", "P10L035"],
        is_composite=True,
        sub_questions=[
            L2SubQuestion(qno="11", answer="a"),
            L2SubQuestion(qno="12", answer="b"),
        ],
    )
    q21 = L2QuestionAnnotation(
        question_number="21",
        question_type="fill_in",
        section_id="选词填空_1",
        shared_material_line_ids=["P2L017"],
        stem_line_ids=["P2L017"],
        answer_line_ids=["P11L034"],
        is_composite=True,
        sub_questions=[L2SubQuestion(qno="21", answer="c")],
    )
    result = _split_no_material_fill_composites([q11, q21])

    assert [q.question_number for q in result] == ["11", "12", "21"]
    assert all(not q.is_composite for q in result[:2])
    assert result[0].answer_line_ids == ["P10L033"]
    assert result[1].answer_line_ids == ["P10L035"]
    assert result[2].is_composite is True


def test_merge_wordbank_fill_composites():
    lines = [
        L1Line("P2L001", 2, 1, 1, "第二节 选词填空", "text"),
        L1Line("P2L002", 2, 2, 2, "pack; confuse; equal; contribute; athlete", "text"),
        L1Line("P2L003", 2, 3, 3, "21. It is too ________ to me.", "text"),
        L1Line("P2L004", 2, 4, 4, "22. Jim is a(n) ________ young boy.", "text"),
    ]
    doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=2, lines=lines)],
        lines=lines,
        source="ppsv3",
        total_pages=2,
    )
    q21 = L2QuestionAnnotation(
        question_number="21",
        question_type="fill_in",
        section_id="选词填空",
        shared_material_line_ids=[],
        stem_line_ids=["P2L003"],
        answer="confusing",
    )
    q22 = L2QuestionAnnotation(
        question_number="22",
        question_type="fill_in",
        section_id="选词填空",
        shared_material_line_ids=[],
        stem_line_ids=["P2L004"],
        answer="athletic",
    )
    q11 = L2QuestionAnnotation(
        question_number="11",
        question_type="fill_in",
        section_id="语法填空",
        shared_material_line_ids=[],
        stem_line_ids=["P2L005"],
        answer="a",
    )
    result = _merge_wordbank_fill_composites([q21, q22, q11], doc)

    assert [q.question_number for q in result] == ["21", "11"]
    assert result[0].is_composite is True
    assert [s.qno for s in result[0].sub_questions] == ["21", "22"]
    assert result[0].shared_material_line_ids == ["P2L002"]
    assert result[0].stem_line_ids == ["P2L002", "P2L003", "P2L004"]
    assert result[1].is_composite is False


def test_annotate_subquestions_do_not_duplicate_parent():
    """母题号和子题号同时出现时，只保留一个归一化后的母题。"""
    doc = _make_simple_doc()
    response = json.dumps({
        "filename": "test.pdf",
        "subject": "物理",
        "questions": [
            {
                "question_number": "16",
                "question_type": "fill_in",
                "section_id": "实验题_16",
                "stem_line_ids": ["P1L001"],
                "options_line_ids": {},
                "score": 10,
            },
            {
                "question_number": "16(1)",
                "question_type": "single_choice",
                "section_id": "实验题_16",
                "stem_line_ids": ["P1L002"],
                "options_line_ids": {"A": ["P1L003"]},
                "score": 2,
            },
        ],
        "metadata_confidence": 0.5,
    })
    gateway = LLMGateway(
        mode="live",
        providers=[MockLLMProvider(response=response)],
    )

    import asyncio
    result = asyncio.run(annotate_document(doc, gateway))
    assert len(result.questions) == 1
    assert result.questions[0].question_number == "16"
    assert result.questions[0].stem_line_ids == ["P1L001", "P1L002"]
    assert result.questions[0].score == 12


def test_subquestion_normalization_feeds_short_answer_anchor_validation():
    """归一化后的复合题保留 LLM 给出的母题/子题行号，仅做校验。"""
    from app.domains.document.anchor_corrector import correct_anchors

    lines = [
        L1Line("P1L001", 1, 1, 1, "15. 某实验题", "text"),
        L1Line("P1L002", 1, 2, 2, "（1）求加速度", "text"),
        L1Line("P1L003", 1, 3, 3, "（2）求质量", "text"),
        L1Line("P1L004", 1, 4, 4, "16. 某实验题", "text"),
        L1Line("P1L005", 1, 5, 5, "（1）选择", "text"),
        L1Line("P1L006", 1, 6, 6, "（2）求值", "text"),
    ]
    doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source="native",
        total_pages=1,
    )
    response = json.dumps({
        "filename": "test.pdf",
        "subject": "物理",
        "questions": [
            {
                "question_number": "15(1)",
                "question_type": "fill_in",
                "section_id": "实验题_15",
                "stem_line_ids": ["P1L001", "P1L002"],
                "options_line_ids": {},
            },
            {
                "question_number": "15(2)",
                "question_type": "fill_in",
                "section_id": "实验题_15",
                "stem_line_ids": ["P1L003"],
                "options_line_ids": {},
            },
            {
                "question_number": "16(1)",
                "question_type": "single_choice",
                "section_id": "实验题_16",
                "stem_line_ids": ["P1L004", "P1L005"],
                "options_line_ids": {},
            },
            {
                "question_number": "16(2)",
                "question_type": "short_answer",
                "section_id": "实验题_16",
                "stem_line_ids": ["P1L006"],
                "options_line_ids": {},
            },
        ],
        "metadata_confidence": 0.5,
    })
    gateway = LLMGateway(
        mode="live",
        providers=[MockLLMProvider(response=response)],
    )

    import asyncio
    annotation = asyncio.run(annotate_document(doc, gateway))
    corrected = correct_anchors(annotation, doc)
    assert len(corrected.questions) == 2
    assert corrected.questions[0].stem_line_ids == ["P1L001", "P1L002", "P1L003"]
    assert corrected.questions[1].stem_line_ids == ["P1L004", "P1L005", "P1L006"]

"""
Phase 2C 测试 — Annotation 原始积累（Structure Signature 采集 + Annotation 版本标记）。

覆盖（PLAN_QUESTION_FAMILY §7.3）：
1. line_annotator prompt 包含 structure_signature 字段说明（object/task/method/condition 四层）
2. LLM 输出 structure_signature → L2QuestionAnnotation 正确解析
3. structure_signature 规范化：非 dict / 空值 → None（不编造）；四层键保留
4. worker llm_annotated_markdown 序列化包含 structure_signature（含 source/confidence/
   annotation_version 元数据）+ annotation_version
"""
import asyncio
import json

import pytest

from app.ai.gateway import LLMGateway
from app.ai.providers import MockLLMProvider
from app.domains.document.line_annotator import (
    ANNOTATION_PROMPT_VERSION,
    _normalize_structure_signature,
    annotate_document,
    build_annotation_prompt,
)
from app.domains.document.schemas_l1 import L1Document, L1Line, L1Page
from app.domains.document.schemas_l2 import L2DocumentAnnotation, L2QuestionAnnotation


def _make_simple_doc() -> L1Document:
    lines = [
        L1Line("P1L001", 1, 1, 1, "一、选择题", "text"),
        L1Line("P1L002", 1, 2, 2, "1. 已知函数f(x)=2x+1，则f(3)=", "text"),
        L1Line("P1L003", 1, 3, 3, "（A）5", "text"),
        L1Line("P1L004", 1, 4, 4, "（B）6", "text"),
        L1Line("P1L005", 1, 5, 5, "（C）7", "text"),
        L1Line("P1L006", 1, 6, 6, "（D）8", "text"),
    ]
    return L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source="native",
        total_pages=1,
    )


# ═══════════════════════════════════════════════════════════════════
# 1. Prompt 包含 structure_signature 字段说明
# ═══════════════════════════════════════════════════════════════════


def test_prompt_contains_structure_signature_instruction():
    """annotation prompt 必须包含 structure_signature 字段说明（含四层）。"""
    doc = _make_simple_doc()
    prompt = build_annotation_prompt(doc)
    assert "structure_signature" in prompt
    assert "object" in prompt
    assert "task" in prompt
    assert "method" in prompt
    assert "condition" in prompt  # Phase 2C 修复：第四层 condition
    assert "Annotation" in prompt  # 明确标注是 Annotation 不是事实


# ═══════════════════════════════════════════════════════════════════
# 2. LLM 输出 structure_signature → 正确解析
# ═══════════════════════════════════════════════════════════════════


def test_annotate_parses_structure_signature():
    """LLM 输出的 structure_signature（含 condition）被解析到 L2QuestionAnnotation。"""
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
                    "A": ["P1L003"], "B": ["P1L004"],
                    "C": ["P1L005"], "D": ["P1L006"],
                },
                "difficulty": 2,
                "knowledge_points": ["函数单调性"],
                "structure_signature": {
                    "object": "函数单调性",
                    "task": "判断单调性",
                    "method": "导数法",
                    "condition": "f(x)=2x+1",
                },
            }
        ],
        "metadata_confidence": 0.9,
    })
    gateway = LLMGateway(mode="live", providers=[MockLLMProvider(response=response)])
    result = asyncio.run(annotate_document(doc, gateway))
    q = result.questions[0]
    assert q.structure_signature == {
        "object": "函数单调性",
        "task": "判断单调性",
        "method": "导数法",
        "condition": "f(x)=2x+1",
    }


def test_annotate_structure_signature_null_when_missing():
    """LLM 未输出 structure_signature → None（不编造）。"""
    doc = _make_simple_doc()
    response = json.dumps({
        "filename": "test.pdf",
        "subject": "数学",
        "questions": [
            {
                "question_number": "1",
                "question_type": "single_choice",
                "stem_line_ids": ["P1L002"],
                "options_line_ids": {"A": ["P1L003"]},
            }
        ],
        "metadata_confidence": 0.9,
    })
    gateway = LLMGateway(mode="live", providers=[MockLLMProvider(response=response)])
    result = asyncio.run(annotate_document(doc, gateway))
    assert result.questions[0].structure_signature is None


# ═══════════════════════════════════════════════════════════════════
# 3. structure_signature 规范化
# ═══════════════════════════════════════════════════════════════════


def test_normalize_structure_signature_valid():
    sig = _normalize_structure_signature({
        "object": "函数", "task": "求值", "method": "直接代入",
        "condition": "f(x)=2x+1", "extra": "忽略",
    })
    assert sig == {
        "object": "函数", "task": "求值", "method": "直接代入",
        "condition": "f(x)=2x+1",
    }


def test_normalize_structure_signature_non_dict():
    assert _normalize_structure_signature("not-a-dict") is None
    assert _normalize_structure_signature(None) is None
    assert _normalize_structure_signature(123) is None


def test_normalize_structure_signature_empty_values():
    assert _normalize_structure_signature(
        {"object": "", "task": " ", "method": None, "condition": ""}
    ) is None


def test_normalize_structure_signature_partial():
    """只提供部分键时保留存在的键。"""
    sig = _normalize_structure_signature({
        "object": "函数", "task": None, "method": "导数法", "condition": None,
    })
    assert sig == {"object": "函数", "method": "导数法"}


def test_normalize_structure_signature_condition_only():
    """只提供 condition（如实验题的条件描述）时保留。"""
    sig = _normalize_structure_signature({"condition": "物体质量 m=2kg，初速度 v0=0"})
    assert sig == {"condition": "物体质量 m=2kg，初速度 v0=0"}


# ═══════════════════════════════════════════════════════════════════
# 4. worker llm_annotated_markdown 序列化
# ═══════════════════════════════════════════════════════════════════


def test_worker_serialization_includes_structure_and_version():
    """worker 序列化的 llm_annotated_markdown 包含 structure_signature（含元数据）+ annotation_version。"""
    from app.worker.document_worker import _serialize_l2_for_persistence

    l2 = L2DocumentAnnotation(
        filename="test.pdf",
        subject="数学",
        questions=[
            L2QuestionAnnotation(
                question_number="1",
                question_type="single_choice",
                stem_line_ids=["P1L002"],
                structure_signature={
                    "object": "函数", "task": "求值", "method": "代入法",
                    "condition": "f(x)=2x+1",
                },
                confidence=0.9,
            )
        ],
    )
    data = _serialize_l2_for_persistence(l2)
    assert data["annotation_version"] == ANNOTATION_PROMPT_VERSION
    sig = data["questions"][0]["structure_signature"]
    assert sig["object"] == "函数"
    assert sig["condition"] == "f(x)=2x+1"
    # Phase 2C 修复：元数据
    assert sig["source"] == "llm"
    assert sig["confidence"] == 0.9
    assert sig["annotation_version"] == ANNOTATION_PROMPT_VERSION


def test_worker_serialization_signature_none_keeps_none():
    """structure_signature 为 None 时，序列化保持 None（不注入元数据）。"""
    from app.worker.document_worker import _serialize_l2_for_persistence

    l2 = L2DocumentAnnotation(
        filename="test.pdf",
        subject="英语",
        questions=[
            L2QuestionAnnotation(
                question_number="1",
                question_type="single_choice",
                stem_line_ids=["P1L002"],
                structure_signature=None,
            )
        ],
    )
    data = _serialize_l2_for_persistence(l2)
    assert data["questions"][0]["structure_signature"] is None


def test_merge_subquestion_group_preserves_structure_signature():
    """综合题子题合并后保留 structure_signature，不再丢弃。"""
    from app.domains.document.line_annotator import _merge_subquestion_group

    sig = {
        "object": "函数",
        "task": "求值",
        "method": "代入法",
        "condition": "f(x)=2x+1",
    }
    q1 = L2QuestionAnnotation(
        question_number="1（1）",
        question_type="fill_in",
        stem_line_ids=["P1L001"],
        structure_signature=sig,
        confidence=0.9,
    )
    q2 = L2QuestionAnnotation(
        question_number="1（2）",
        question_type="fill_in",
        stem_line_ids=["P1L002"],
        confidence=0.8,
    )

    merged = _merge_subquestion_group([q1, q2], "1")

    assert merged.structure_signature == sig


def test_build_wordbank_composite_preserves_structure_signature():
    """选词填空综合题合并后保留 structure_signature。"""
    from app.domains.document.line_annotator import _build_wordbank_composite

    sig = {
        "object": "词汇辨析",
        "task": "选择正确词形",
        "method": "语境判断",
        "condition": "word bank",
    }
    doc = _make_simple_doc()
    q1 = L2QuestionAnnotation(
        question_number="1",
        question_type="fill_in",
        section_id="word_bank_1",
        stem_line_ids=["P1L002"],
        structure_signature=sig,
        confidence=0.9,
    )
    q2 = L2QuestionAnnotation(
        question_number="2",
        question_type="fill_in",
        section_id="word_bank_1",
        stem_line_ids=["P1L003"],
        confidence=0.8,
    )

    merged = _build_wordbank_composite([q1, q2], doc)

    assert merged.structure_signature == sig

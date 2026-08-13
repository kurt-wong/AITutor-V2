"""
内容切片器 — CorrectedAnchor + L1 原文 → SlicedQuestion。

用校正后锚点从 L1 切片 stem/options，代码切片，不依赖 LLM 抄写。
遵守 V1_LESSONS 3.1（信息零损耗）。

详见 Docs/01_Product/T3_IMPLEMENTATION.md §8 Task 1.4。
"""

from __future__ import annotations

import logging
import re

from app.domains.document.schemas_l1 import L1Document, L1Line
from app.domains.document.schemas_l2 import (
    CorrectedAnchor,
    L2DocumentAnnotation,
    L2QuestionAnnotation,
    SlicedQuestion,
)

logger = logging.getLogger(__name__)

# LLM 题型枚举归一化：不同 LLM 可能输出不同变体，统一到 canonical 值
_QUESTION_TYPE_CANONICAL = {
    "fill_blank": "fill_in",
    "fill_in_blank": "fill_in",
    "fill_in_the_blank": "fill_in",
    "填空": "fill_in",
    "填空题": "fill_in",
    "fill": "fill_in",
    "choice": "single_choice",
    "single_choice": "single_choice",
    "选择": "single_choice",
    "选择题": "single_choice",
    "单选": "single_choice",
    "单选题": "single_choice",
    "单项选择": "single_choice",
    "单项选择题": "single_choice",
    "多选": "multiple_choice",
    "multiple_choice": "multiple_choice",
    "多选题": "multiple_choice",
    "多项选择": "multiple_choice",
    "true_false": "true_false",
    "判断题": "true_false",
    "short_answer": "short_answer",
    "简答题": "short_answer",
    "解答题": "short_answer",
    "计算题": "short_answer",
}


def _canonical_question_type(qt: str) -> str:
    """将 LLM 输出的题型归一化为 canonical 枚举。"""
    return _QUESTION_TYPE_CANONICAL.get(qt, qt)


def slice_questions(
    annotation: L2DocumentAnnotation,
    doc: L1Document,
) -> list[SlicedQuestion]:
    """用校正后锚点从 L1 切片题目内容。"""
    line_by_id = {l.line_id: l for l in doc.lines}
    sliced: list[SlicedQuestion] = []
    anchor_map = _build_anchor_map(annotation)

    for question in annotation.questions:
        sq = _slice_single_question(question, line_by_id, anchor_map)
        sliced.append(sq)

    logger.info(
        "content_slicing questions=%d sliced=%d",
        len(annotation.questions),
        len(sliced),
    )

    return sliced


def _build_anchor_map(annotation: L2DocumentAnnotation) -> dict:
    """构建 question_number → {field: CorrectedAnchor} 映射。

    使用 CorrectedAnchor.question_number 直接分组，
    不依赖顺序索引，避免 anchor 错位。
    """
    result: dict[str, dict[str, "CorrectedAnchor"]] = {}
    for anchor in annotation.corrected_anchors:
        q_num = anchor.question_number
        if not q_num:
            continue
        if q_num not in result:
            result[q_num] = {}
        result[q_num][anchor.field] = anchor
    return result


def _slice_single_question(
    question: L2QuestionAnnotation,
    line_by_id: dict[str, L1Line],
    anchor_map: dict,
) -> SlicedQuestion:
    """切片单个题目。"""
    stem = _slice_lines(question.stem_line_ids, line_by_id)
    options = _slice_options(question.options_line_ids, line_by_id)

    # 获取 anchors
    q_anchors = anchor_map.get(question.question_number, {})
    stem_anchor = q_anchors.get("stem")
    # 合并所有 option anchors 为 options_anchor 列表
    option_anchors = [v for k, v in q_anchors.items() if k.startswith("option_")]

    # 构建 options_anchor: 合并所有选项锚点
    options_anchor = None
    if option_anchors:
        all_llm_ids = []
        all_corrected_ids = []
        statuses = [a.anchor_status for a in option_anchors]
        for a in option_anchors:
            all_llm_ids.extend(a.llm_line_ids)
            all_corrected_ids.extend(a.corrected_line_ids)
        if "missing" in statuses:
            worst_status = "missing"
        elif "retry" in statuses:
            worst_status = "retry"
        elif "nearest" in statuses:
            worst_status = "nearest"
        else:
            worst_status = "exact"
        options_anchor = CorrectedAnchor(
            field="options",
            llm_line_ids=all_llm_ids,
            corrected_line_ids=all_corrected_ids,
            anchor_status=worst_status,
            validation_passed=worst_status in ("exact", "nearest"),
            question_number=question.question_number,
        )

    # 全部锚点（stem + options）
    all_anchors = [a for a in [stem_anchor] if a]
    all_anchors.extend(option_anchors)

    return SlicedQuestion(
        question_number=question.question_number,
        question_type=_canonical_question_type(question.question_type),
        stem=stem,
        options=options,
        section_id=question.section_id,
        difficulty=question.difficulty,
        score=question.score,
        knowledge_points=question.knowledge_points,
        confidence=question.confidence,
        stem_anchor=stem_anchor,
        options_anchor=options_anchor,
        corrected_anchors=all_anchors,
        source_page=question.source_page,
    )


def _slice_lines(
    line_ids: list[str],
    line_by_id: dict[str, L1Line],
) -> str:
    """按行 ID 列表切片文本，行间用换行连接。"""
    parts: list[str] = []
    for lid in line_ids:
        line = line_by_id.get(lid)
        if line:
            parts.append(line.text)
    return "\n".join(parts)


def _slice_options(
    options_line_ids: dict[str, list[str]],
    line_by_id: dict[str, L1Line],
) -> list[dict[str, str]]:
    """切片选项，返回 [{"label": "A", "text": "..."}] 列表。"""
    result: list[dict[str, str]] = []
    for label in sorted(options_line_ids.keys()):
        lids = options_line_ids[label]
        text_parts: list[str] = []
        for lid in lids:
            line = line_by_id.get(lid)
            if line:
                text = _strip_option_label(line.text, label)
                text_parts.append(text)
        result.append({
            "label": label,
            "text": " ".join(text_parts).strip(),
        })
    return result


def _strip_option_label(text: str, label: str) -> str:
    """去掉选项标签前缀。"""
    patterns = [
        rf"^[（(]\s*{re.escape(label)}\s*[）)]\s*",
        rf"^{re.escape(label)}\s*[.、．]\s*",
    ]
    for pattern in patterns:
        text = re.sub(pattern, "", text)
    return text.strip()

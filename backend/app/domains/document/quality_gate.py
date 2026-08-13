"""
质量门 — 按题评估切片质量，生成 confidence + issues。

按题检查：切片完整、选项数量、答案匹配、anchor_status。
失败只标低置信度，不整批丢弃（V1_LESSONS 3.20）。
missing/retry 不允许自动发布。

详见 Docs/01_Product/T3_IMPLEMENTATION.md §8 Task 1.6。
"""

from __future__ import annotations

import logging

from app.domains.document.schemas_l2 import SlicedQuestion

logger = logging.getLogger(__name__)

_SINGLE_CHOICE_OPTION_COUNT = 4


def evaluate_quality(
    sliced_questions: list[SlicedQuestion],
) -> list[SlicedQuestion]:
    """评估每个题目的切片质量。"""
    for sq in sliced_questions:
        issues: list[str] = []
        score = 1.0

        # 0. 检查锚点状态（最高优先级）
        anchor_status = _get_anchor_status(sq)
        if anchor_status == "missing":
            issues.append("锚点缺失，禁止自动发布")
            score -= 0.5
        elif anchor_status == "retry":
            issues.append("锚点需重新标注，禁止自动发布")
            score -= 0.4

        # 1. 检查题干是否为空
        if not sq.stem or sq.stem.strip() == "":
            issues.append("题干为空")
            score -= 0.5

        # 2. 检查选择题选项数量
        if sq.question_type in ("single_choice", "multiple_choice"):
            expected = _SINGLE_CHOICE_OPTION_COUNT
            actual = len(sq.options)
            if actual == 0:
                issues.append("选项锚点缺失，禁止自动发布")
                score -= 0.5
            elif actual < expected:
                issues.append(f"选项数量不足: {actual}/{expected}")
                score -= 0.3
            elif actual > expected:
                issues.append(f"选项数量过多: {actual}/{expected}")
                score -= 0.1

        # 3. 检查答案是否匹配
        if sq.answer is None and sq.answer_provenance:
            if sq.answer_provenance.source == "llm_fallback":
                issues.append("答案依赖 LLM 兜底")
                score -= 0.2

        # 4. 检查详解是否匹配
        if sq.explanation is None and sq.explanation_provenance:
            if sq.explanation_provenance.source == "llm_fallback":
                issues.append("详解依赖 LLM 兜底")
                score -= 0.1

        # 5. 检查答案缺失
        if sq.answer_provenance and sq.answer_provenance.source == "llm_fallback":
            if not sq.answer:
                issues.append("答案缺失，禁止自动发布")
                score -= 0.3

        confidence = max(0.0, min(1.0, score))
        sq.confidence = confidence
        sq.issues = issues

    high_conf = sum(1 for sq in sliced_questions if sq.confidence >= 0.8)
    low_conf = sum(1 for sq in sliced_questions if sq.confidence < 0.5)
    blocked = sum(
        1 for sq in sliced_questions
        if any("禁止自动发布" in i for i in sq.issues)
    )

    logger.info(
        "quality_gate total=%d high_confidence=%d low_confidence=%d blocked=%d",
        len(sliced_questions),
        high_conf,
        low_conf,
        blocked,
    )

    return sliced_questions


def _get_anchor_status(sq: SlicedQuestion) -> str:
    """从 SlicedQuestion 提取最差的锚点状态。"""
    statuses = []
    if sq.stem_anchor:
        statuses.append(sq.stem_anchor.anchor_status)
    if sq.options_anchor:
        statuses.append(sq.options_anchor.anchor_status)
    # 也检查 corrected_anchors 中的所有锚点
    for a in sq.corrected_anchors:
        statuses.append(a.anchor_status)

    if not statuses:
        return "unknown"

    if "missing" in statuses:
        return "missing"
    if "retry" in statuses:
        return "retry"
    if "nearest" in statuses:
        return "nearest"
    return "exact"

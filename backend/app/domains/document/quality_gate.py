"""
质量门 — 按题评估切片质量，生成 confidence + issues。

按题检查：切片完整、选项数量、答案匹配、anchor_status。
失败只标低置信度，不整批丢弃（V1_LESSONS 3.20）。
missing/retry 不允许自动发布。

详见 Docs/01_Product/T3_IMPLEMENTATION.md §8 Task 1.6。
"""

from __future__ import annotations

import logging
import re

from app.domains.document.schemas_l2 import SlicedQuestion

logger = logging.getLogger(__name__)

_SINGLE_CHOICE_OPTION_COUNT = 4

# 答案内容可疑检测（WP3：堵住 document_answer_table 高置信度错误路径）
_PUA_RE = re.compile(r"[\ue000-\uf8ff]")
_REPLACEMENT_RE = re.compile(r"\ufffd")
# 只检测真正无意义的 LaTeX 残留（孤立反斜杠、乱码命令），不检测合法数学命令
# 合法命令如 \left \frac \pi \right \sqrt \in 等在解答题答案中常见（$ 定界符丢失）
_MEANINGLESS_LATEX_RE = re.compile(r"\\[^a-zA-Z\s]|\\(?:end|begin)\{[^}]*\}")
_MATH_DOLLAR_RE = re.compile(r"\$[^$]*\$")
_PUNCT_ONLY_RE = re.compile(r"[\s，。；：、.．!！?？\-—…]+")
_SEVEN_CHOICE_RE = re.compile(r"七选五|7选5|7选七")

# P0-4 修复（bugs.md BUG-012 §三 B/D）：
# 题干异常膨胀检测 —— 拦截"综合题材料整段并入题干"类缺陷。
# 阈值设计（保守防误伤）：
# - 非综合题正常题干通常 < 200 字符（含公式/图注）；材料混入可达 1000+。
# - 综合题（完形/阅读）材料+子题合理上限约 3000 字符；超过说明材料被重复复制或错切。
_STEM_CHAR_LIMIT_NON_COMPOSITE = 800
_STEM_CHAR_LIMIT_COMPOSITE = 3000


def _expected_option_count(sq) -> int:
    """返回选择题期望选项数；七选五为 7，其余为 4。"""
    section_id = sq.section_id or ""
    if _SEVEN_CHOICE_RE.search(section_id):
        return 7
    return _SINGLE_CHOICE_OPTION_COUNT


def _unpaired_latex(text: str) -> bool:
    """检测 $...$ 之外的无意义 LaTeX 残留（合法数学命令不算可疑）。"""
    without_math = _MATH_DOLLAR_RE.sub("", text or "")
    return bool(_MEANINGLESS_LATEX_RE.search(without_math))


def _answer_text_suspicious(answer_text: str) -> bool:
    """答案文本是否含可疑内容（PUA/替换符/未解析 LaTeX/空）。"""
    if answer_text is None or answer_text.strip() == "":
        return False  # 空答案由"答案缺失"检查处理
    if _PUA_RE.search(answer_text):
        return True
    if _REPLACEMENT_RE.search(answer_text):
        return True
    if _unpaired_latex(answer_text):
        return True
    return False


def evaluate_quality(
    sliced_questions: list[SlicedQuestion],
) -> list[SlicedQuestion]:
    """评估每个题目的切片质量。"""
    for sq in sliced_questions:
        # 保留 slicer 阶段已有的 issues（如 section_id 校验）
        issues: list[str] = list(sq.issues) if sq.issues else []
        score = 1.0

        # 已有 issues 对应的扣分（每条 -0.05）
        score -= len(issues) * 0.05

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

        # 1.5 题干异常膨胀检测（P0-4：拦截综合题材料整段并入题干）
        # 背景：英语完形/阅读题材料被整段写入 stem（见审计报告 §三 D），
        # 单题 stem 可达 2000-2600 字符。正常单题题干远小于阈值。
        stem_len = len(sq.stem or "")
        limit = (
            _STEM_CHAR_LIMIT_COMPOSITE if getattr(sq, "is_composite", False)
            else _STEM_CHAR_LIMIT_NON_COMPOSITE
        )
        if stem_len > limit:
            issues.append(f"题干异常膨胀: {stem_len} 字符 (上限 {limit})，疑似共享材料整段并入")
            score -= 0.4

        # 2. 检查选择题选项数量
        if sq.question_type in ("single_choice", "multiple_choice"):
            expected = _expected_option_count(sq)
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

        # 3.5 答案内容可疑检查（WP3：堵住 document_answer_table 高置信度错误路径）
        # 触发条件：answer_matcher 标记的"答案可疑"、答案表低置信度来源、
        #          答案文本含 PUA/替换符/未解析 LaTeX
        answer_suspicious = any("答案可疑" in i for i in issues)
        if (sq.answer_provenance
                and sq.answer_provenance.source == "document_answer_table"
                and sq.answer_provenance.confidence < 0.8):
            answer_suspicious = True
        if _answer_text_suspicious(sq.answer):
            answer_suspicious = True
        if answer_suspicious:
            issues.append("答案可疑，禁止自动发布")
            score -= 0.5

        # 3.6 LLM 行号切片质量：空切片/纯标点不能作为答案发布
        if (sq.answer_provenance
                and sq.answer_provenance.source == "llm_annotation"):
            answer_text = (sq.answer or "").strip()
            if not answer_text or _PUNCT_ONLY_RE.fullmatch(answer_text):
                issues.append("LLM 答案切片为空或仅标点，禁止自动发布")
                score -= 0.5
            if not sq.answer_line_ids:
                issues.append("LLM 答案缺少有效行号，禁止自动发布")
                score -= 0.4

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

        # 注意：section_id 校验已在 content_slicer 阶段完成
        # quality_gate 无法可靠判断题目是否属于共享材料，不做此检查

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
    if "fuzzy" in statuses:
        return "fuzzy"
    if "semantic" in statuses:
        return "semantic"
    return "exact"

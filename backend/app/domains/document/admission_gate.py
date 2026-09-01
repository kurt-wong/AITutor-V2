"""
Admission Gate — 逐题入库门禁。

三态决策：approve / review / reject，基于 13 条硬规则的确定性校验。
LLM 每次解析完 → 逐题过 gate → approved 入 questions 表 → review/reject 入
question_candidates 表。

与 quality_gate 的关系：
- quality_gate: LLM 标注阶段打分，标记 issues/confidence
- admission_gate: 入库前终审，决定 approve/review/reject
- admission_gate 不修改 confidence/issues，只做终审决策
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from app.domains.document.content_hash import normalize_text
from app.domains.document.schemas_l2 import (
    SlicedQuestion,
    SourceProvenance,
)

logger = logging.getLogger(__name__)

# ── 答案可信来源白名单 ──────────────────────────────────────────────
_TRUSTED_ANSWER_SOURCES = {
    "document_answer_table",
    "document_inline_answer",
    "document_solution_answer",
    "native_extract",
    "ocr_extract",
}

# 选择题标签
_CHOICE_LABELS_STANDARD = ["A", "B", "C", "D", "E", "F", "G"]

# 非综合题选项数量上限
_NON_COMPOSITE_MAX_OPTIONS = 7

# LLM 可靠标注模式
_LLM_RELIABLE_TYPES = {"single_choice", "multiple_choice", "true_false", "cloze", "seven_to_five"}

# R12 正则预编译（模块级，避免每次调用重编译）
_PUA_RE = re.compile(r"[-\U000f0000-\U000ffffd\U00100000-\U0010fffd]")
_REPLACEMENT_RE = re.compile(r"�")
_INVISIBLE_RE = re.compile(r"[​-‏ - ⁠-⁯﻿]")
_PUNCT_ONLY_RE = re.compile(r"^[\s，。；：、.．!！?？\-—…]+$")


# ── 决策结果 ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class AdmissionCheck:
    """单条校验规则结果。"""

    rule: str         # 规则名（snake_case）
    passed: bool      # 是否通过
    severity: str     # "reject" / "review" / "metadata"
    message: str      # 人类可读原因


@dataclass
class AdmissionDecision:
    """逐题门禁决策结果。"""

    decision: str = "approve"  # approve / review / reject
    checks: list[AdmissionCheck] = field(default_factory=list)
    reject_reason: str | None = None
    review_reason: str | None = None

    @property
    def passed(self) -> bool:
        return self.decision == "approve"

    def add_check(self, check: AdmissionCheck) -> None:
        self.checks.append(check)


# ── 校验规则（13 条） ──────────────────────────────────────────────


def _check_R01_stem_non_empty(sq: SlicedQuestion) -> AdmissionCheck:
    """R01: stem 非空。"""
    has_stem = bool(sq.stem and sq.stem.strip())
    return AdmissionCheck(
        rule="R01_stem_non_empty",
        passed=has_stem,
        severity="reject",
        message="题干为空" if not has_stem else "",
    )


def _check_R02_no_stem_options_in_answer(sq: SlicedQuestion) -> AdmissionCheck:
    """R02: answer 不包含 stem/options 文本。"""
    answer = (sq.answer or "").strip()
    if not answer:
        return AdmissionCheck("R02_no_stem_options_in_answer", True, "reject", "")

    stem = (sq.stem or "").strip()
    answer_normalized = normalize_text(answer)
    stem_normalized = normalize_text(stem)

    # 短路：answer 完全等于 stem → 数据质量问题（答案不应与题干相同）
    if stem_normalized and answer_normalized and stem_normalized == answer_normalized:
        return AdmissionCheck(
            "R02_no_stem_options_in_answer",
            False,
            "reject",
            f"答案与题干完全相同 ({len(answer)} chars)",
        )

    # 如果答案包含题干超过 80%，说明答案里混入了题干内容
    if stem_normalized and len(stem_normalized) > 20:
        if stem_normalized in answer_normalized or (
            len(answer_normalized) > 0
            and len(stem_normalized) > 0
            and _text_overlap_ratio(answer_normalized, stem_normalized) >= 0.8
        ):
            return AdmissionCheck(
                "R02_no_stem_options_in_answer",
                False,
                "reject",
                f"答案包含题干文本 ({len(answer)} chars)",
            )

    # 检查答案是否包含多个选项文本（说明选项被并入答案）
    if sq.options:
        option_texts = [normalize_text(o.get("text", "")) for o in sq.options if o.get("text")]
        matched_options = sum(1 for t in option_texts if t and t in answer_normalized)
        if matched_options >= 3:
            return AdmissionCheck(
                "R02_no_stem_options_in_answer",
                False,
                "reject",
                f"答案包含 {matched_options} 个选项文本，疑似吞并选项",
            )

    return AdmissionCheck("R02_no_stem_options_in_answer", True, "reject", "")


def _check_R03_stem_length_sane(sq: SlicedQuestion) -> AdmissionCheck:
    """R03: stem 长度合理。"""
    stem_len = len(sq.stem or "")
    is_composite = getattr(sq, "is_composite", False)
    has_material = bool(getattr(sq, "shared_material_line_ids", None)) or (
        "材料" in (sq.stem or "")
    )
    is_short_answer = sq.question_type == "short_answer"
    limit = 3000 if (is_composite or has_material or is_short_answer) else 800
    passed = stem_len <= limit
    return AdmissionCheck(
        "R03_stem_length_sane",
        passed,
        "reject",
        f"题干 {stem_len} 字符超过上限 {limit}" if not passed else "",
    )


def _check_R04_options_count_sane(sq: SlicedQuestion) -> AdmissionCheck:
    """R04: 选择题选项数量合理（按题型检查最小/最大）。"""
    if sq.question_type not in ("single_choice", "multiple_choice", "true_false"):
        return AdmissionCheck("R04_options_count_sane", True, "reject", "")

    if getattr(sq, "is_composite", False):
        return AdmissionCheck("R04_options_count_sane", True, "reject", "")

    option_count = len(sq.options or [])

    # true_false 固定 2 选项
    if sq.question_type == "true_false":
        if option_count != 2:
            return AdmissionCheck(
                "R04_options_count_sane",
                False,
                "reject",
                f"判断题应有 2 个选项，实际 {option_count}",
            )
        return AdmissionCheck("R04_options_count_sane", True, "reject", "")

    # single_choice / multiple_choice: 最少 3 选项（A/B/C），最多 7
    if option_count == 0:
        return AdmissionCheck(
            "R04_options_count_sane", False, "reject", "选择题选项数为 0"
        )
    if option_count < 3:
        return AdmissionCheck(
            "R04_options_count_sane",
            False,
            "review",
            f"选择题选项数偏少: {option_count} < 3（标准 A/B/C）",
        )
    if option_count > _NON_COMPOSITE_MAX_OPTIONS:
        return AdmissionCheck(
            "R04_options_count_sane",
            False,
            "reject",
            f"选项数量异常: {option_count} > {_NON_COMPOSITE_MAX_OPTIONS}",
        )
    return AdmissionCheck("R04_options_count_sane", True, "reject", "")


def _check_R05_choice_labels_match(sq: SlicedQuestion) -> AdmissionCheck:
    """R05: 选择题选项标签匹配。"""
    if sq.question_type not in ("single_choice", "multiple_choice"):
        return AdmissionCheck("R05_choice_labels_match", True, "reject", "")

    if getattr(sq, "is_composite", False):
        return AdmissionCheck("R05_choice_labels_match", True, "reject", "")

    if not sq.options:
        return AdmissionCheck("R05_choice_labels_match", True, "reject", "")

    labels = [o.get("label", "").strip().upper() for o in sq.options]
    expected = _CHOICE_LABELS_STANDARD[: len(sq.options)]
    if sorted(labels) != sorted(expected):
        return AdmissionCheck(
            "R05_choice_labels_match",
            False,
            "review",
            f"选项标签不规范: {labels}，期望 {expected}",
        )
    return AdmissionCheck("R05_choice_labels_match", True, "reject", "")


def _check_R06_answer_provenance_trusted(sq: SlicedQuestion) -> AdmissionCheck:
    """R06: 答案来源可信 + 置信度足够。"""
    provenance = getattr(sq, "answer_provenance", None)
    if not provenance:
        return AdmissionCheck("R06_answer_provenance_trusted", False, "review", "答案无来源标记")

    confidence = getattr(provenance, "confidence", None)
    if confidence is None:
        confidence = 1.0
    _CONFIDENCE_THRESHOLD = 0.5

    if provenance.source in _TRUSTED_ANSWER_SOURCES:
        if confidence < _CONFIDENCE_THRESHOLD:
            return AdmissionCheck(
                "R06_answer_provenance_trusted",
                False,
                "review",
                f"来源可信({provenance.source})但置信度低({confidence:.2f}<{_CONFIDENCE_THRESHOLD})",
            )
        return AdmissionCheck("R06_answer_provenance_trusted", True, "review", "")
    if provenance.source == "llm_annotation":
        if sq.question_type in _LLM_RELIABLE_TYPES:
            if confidence < _CONFIDENCE_THRESHOLD:
                return AdmissionCheck(
                    "R06_answer_provenance_trusted",
                    False,
                    "review",
                    f"LLM标注可靠题型但置信度低({confidence:.2f})",
                )
            return AdmissionCheck("R06_answer_provenance_trusted", True, "review", "")
        else:
            return AdmissionCheck(
                "R06_answer_provenance_trusted",
                False,
                "review",
                f"答案来源 llm_annotation + 题型 {sq.question_type}，准确性不确定",
            )
    if provenance.source == "llm_fallback":
        return AdmissionCheck(
            "R06_answer_provenance_trusted",
            False,
            "review",
            "答案来源 llm_fallback，准确性不确定",
        )
    return AdmissionCheck("R06_answer_provenance_trusted", False, "review", f"答案来源 {provenance.source} 不可信")


def _check_R07_no_duplicate_answer_sources(sq: SlicedQuestion) -> AdmissionCheck:
    """R07: 答案/详解来源一致性检查。

    当前数据模型中 answer_provenance 是单个 SourceProvenance，
    不存在同一字段的多来源冲突。此规则改为检查跨字段一致性：
    - answer 可信 + explanation 不可信 → review
    - 两者都来自 llm_fallback → review
    """
    answer_prov = getattr(sq, "answer_provenance", None)
    explanation_prov = getattr(sq, "explanation_provenance", None)

    # 无来源信息时不检查
    if not answer_prov:
        return AdmissionCheck("R07_no_duplicate_answer_sources", True, "review", "")

    answer_trusted = answer_prov.source in _TRUSTED_ANSWER_SOURCES
    explanation_from_llm = (
        explanation_prov is not None
        and explanation_prov.source in ("llm_annotation", "llm_fallback")
    )

    # answer 来自可信来源，但 explanation 来自 LLM → 一致性风险
    if answer_trusted and explanation_from_llm:
        return AdmissionCheck(
            "R07_no_duplicate_answer_sources",
            False,
            "review",
            f"答案来源可信({answer_prov.source})，但详解来自 LLM({explanation_prov.source})",
        )

    # 两者都来自 LLM fallback → 双重不确定性
    if (
        answer_prov.source == "llm_fallback"
        and explanation_prov is not None
        and explanation_prov.source == "llm_fallback"
    ):
        return AdmissionCheck(
            "R07_no_duplicate_answer_sources",
            False,
            "review",
            "答案和详解均来自 LLM fallback，双重不确定性",
        )

    return AdmissionCheck("R07_no_duplicate_answer_sources", True, "review", "")


def _check_R08_slice_consistency(
    sq: SlicedQuestion, l1_lines: list[dict] | None
) -> AdmissionCheck:
    """R08: 行号回填一致性（最关键校验）。

    如果有 l1_lines 提供 L1 原文，检查行号切片后文本与入库字段一致。
    无 l1_lines 时只做基本空值检查。
    """
    if not sq.stem_line_ids:
        return AdmissionCheck("R08_slice_consistency", False, "review", "stem 无行号引用")

    if l1_lines is None or not l1_lines:
        return AdmissionCheck("R08_slice_consistency", False, "review", "无 L1 原文可比对，无法验证行号一致性")

    sliced_stem = _slice_by_line_ids(sq.stem_line_ids, l1_lines)
    if not sliced_stem:
        return AdmissionCheck("R08_slice_consistency", False, "reject", "行号切片结果为空")

    stem_norm = normalize_text(sq.stem or "")
    sliced_norm = normalize_text(sliced_stem)

    if not stem_norm or not sliced_norm:
        return AdmissionCheck("R08_slice_consistency", True, "review", "")

    overlap = _text_overlap_ratio(stem_norm, sliced_norm)
    if overlap < 0.7:
        return AdmissionCheck(
            "R08_slice_consistency",
            False,
            "reject",
            f"行号切片文本与 stem 不一致 (overlap={overlap:.0%})",
        )

    return AdmissionCheck("R08_slice_consistency", True, "review", "")


def _check_R09_explanation_not_answer(sq: SlicedQuestion) -> AdmissionCheck:
    """R09: explanation 不是答案的重复。"""
    explanation = (sq.explanation or "").strip()
    answer = (sq.answer or "").strip()
    if not explanation or not answer:
        return AdmissionCheck("R09_explanation_not_answer", True, "review", "")

    if normalize_text(explanation) == normalize_text(answer):
        return AdmissionCheck(
            "R09_explanation_not_answer",
            False,
            "review",
            "详解与答案完全相同，疑似切片错误",
        )
    return AdmissionCheck("R09_explanation_not_answer", True, "review", "")


def _check_R10_explanation_length_sane(sq: SlicedQuestion) -> AdmissionCheck:
    """R10: explanation 长度合理（>3 字符）。"""
    explanation = (sq.explanation or "").strip()
    if not explanation:
        return AdmissionCheck("R10_explanation_length_sane", True, "metadata", "")
    if len(explanation) <= 3:
        return AdmissionCheck(
            "R10_explanation_length_sane",
            False,
            "metadata",
            f"详解过短: {len(explanation)} 字符",
        )
    return AdmissionCheck("R10_explanation_length_sane", True, "metadata", "")


def _check_R11_metadata_completeness(sq: SlicedQuestion) -> AdmissionCheck:
    """R11: 元数据完整性。关键字段缺失 → review；非关键缺失 → metadata。"""
    critical_missing = []
    minor_missing = []

    if not getattr(sq, "score", None):
        critical_missing.append("score")
    if not getattr(sq, "difficulty", None):
        critical_missing.append("difficulty")
    if not getattr(sq, "section_id", None):
        minor_missing.append("section_id")
    if not getattr(sq, "knowledge_points", None):
        minor_missing.append("knowledge_points")

    if critical_missing:
        return AdmissionCheck(
            "R11_metadata_completeness",
            False,
            "review",
            f"关键元数据缺失: {', '.join(critical_missing)}",
        )
    if minor_missing:
        return AdmissionCheck(
            "R11_metadata_completeness",
            False,
            "metadata",
            f"非关键元数据缺失: {', '.join(minor_missing)}",
        )
    return AdmissionCheck("R11_metadata_completeness", True, "metadata", "")


def _check_R12_answer_content_sane(sq: SlicedQuestion) -> AdmissionCheck:
    """R12: 答案内容合理性。"""
    answer = (sq.answer or "").strip()
    if not answer:
        return AdmissionCheck("R12_answer_content_sane", True, "review", "")

    # PUA/替换符/不可见字符检测（覆盖 BMP + SMP + SIP PUA）
    # PUA/替换符/不可见字符检测（使用模块级预编译正则）
    if _PUA_RE.search(answer) or _REPLACEMENT_RE.search(answer) or _INVISIBLE_RE.search(answer):
        return AdmissionCheck(
            "R12_answer_content_sane",
            False,
            "reject",
            "答案含 PUA/替换符/不可见字符，可能损坏",
        )

    # 答案仅标点
    if _PUNCT_ONLY_RE.fullmatch(answer):
        return AdmissionCheck(
            "R12_answer_content_sane",
            False,
            "reject",
            "答案仅包含标点",
        )

    return AdmissionCheck("R12_answer_content_sane", True, "review", "")


def _check_R13_composite_answer_format(sq: SlicedQuestion) -> AdmissionCheck:
    """R13: 综合题答案格式。"""
    if not getattr(sq, "is_composite", False):
        return AdmissionCheck("R13_composite_answer_format", True, "review", "")

    if not sq.sub_questions:
        return AdmissionCheck(
            "R13_composite_answer_format",
            False,
            "review",
            "综合题标记但无子题",
        )

    subs_with_answer = sum(
        1 for s in sq.sub_questions
        if getattr(s, "answer", None) and getattr(s, "answer", None).strip()
    )
    if subs_with_answer == 0:
        return AdmissionCheck(
            "R13_composite_answer_format",
            False,
            "review",
            f"综合题 {len(sq.sub_questions)} 个子题均无答案",
        )

    return AdmissionCheck("R13_composite_answer_format", True, "review", "")


def _check_R14_shared_material_exists(sq: SlicedQuestion) -> AdmissionCheck:
    """R14: 材料型综合题必须有共享材料。"""
    if not getattr(sq, "is_composite", False):
        return AdmissionCheck("R14_shared_material_exists", True, "review", "")

    has_material_ids = bool(getattr(sq, "shared_material_line_ids", None))
    has_material_text = bool(getattr(sq, "shared_material", None))

    # 宽泛检测：茎中提及材料/阅读/内容/图表/下文 等关键词
    stem_lower = (sq.stem or "").lower()
    material_keywords = ["材料", "阅读", "内容", "图表", "下文", "文章",
                         "段落", "短文", "对话", " passage", "读图"]
    has_material_hint = any(kw in stem_lower for kw in material_keywords)

    if has_material_hint and not has_material_ids and not has_material_text:
        return AdmissionCheck(
            "R14_shared_material_exists",
            False,
            "review",
            "综合题提及材料/内容但 shared_material 缺失",
        )

    # 即使茎中无关键词，有 shared_material_line_ids 但无 shared_material 也应 review
    if has_material_ids and not has_material_text:
        return AdmissionCheck(
            "R14_shared_material_exists",
            False,
            "review",
            "有 shared_material_line_ids 但 shared_material 文本缺失",
        )

    return AdmissionCheck("R14_shared_material_exists", True, "review", "")


def _check_R15_word_bank_for_cloze(sq: SlicedQuestion) -> AdmissionCheck:
    """R15: 选词填空/词汇填空必须有词库。

    只检查 word_fill / vocabulary_fill / wordbank_fill——这些题型
    依赖词库供选词，没有 word_bank 则无法作答。
    其他填空类型（grammar_fill / cloze / seven_to_five / fill_in）
    不依赖词库，不应触发此规则。
    """
    word_bank_types = {"word_fill", "vocabulary_fill", "wordbank_fill"}
    if sq.question_type not in word_bank_types:
        return AdmissionCheck("R15_word_bank_for_cloze", True, "review", "")

    word_bank = getattr(sq, "word_bank", None)
    if not word_bank or not isinstance(word_bank, list) or len(word_bank) == 0:
        return AdmissionCheck(
            "R15_word_bank_for_cloze",
            False,
            "review",
            f"选词填空题({sq.question_type})缺少词库 word_bank",
        )

    return AdmissionCheck("R15_word_bank_for_cloze", True, "review", "")


def _check_R16_images_have_metadata(
    sq: SlicedQuestion, question_images: list[dict] | None = None,
) -> AdmissionCheck:
    """R16: 有图题必须有完整的图片元数据（answer_images + question_images）。"""
    all_images = list(getattr(sq, "answer_images", None) or [])
    if question_images:
        all_images.extend(question_images)

    if not all_images:
        return AdmissionCheck("R16_images_have_metadata", True, "review", "")

    incomplete = []
    for i, img in enumerate(all_images):
        missing = []
        if not img.get("page_no") and not img.get("xref"):
            missing.append("page_no/xref")
        if not img.get("bbox") and not img.get("url"):
            missing.append("bbox/url")
        if not img.get("source"):
            missing.append("source")
        if missing:
            incomplete.append(f"img[{i}]:缺{','.join(missing)}")

    if incomplete:
        return AdmissionCheck(
            "R16_images_have_metadata",
            False,
            "review",
            f"图片元数据不完整: {'; '.join(incomplete[:3])}",
        )

    return AdmissionCheck("R16_images_have_metadata", True, "review", "")


def _check_R17_sub_question_completeness(sq: SlicedQuestion) -> AdmissionCheck:
    """R17: 综合题子题必须完整（qno + stem + answer，选择题还要 options）。"""
    if not getattr(sq, "is_composite", False):
        return AdmissionCheck("R17_sub_question_completeness", True, "review", "")

    sub_questions = sq.sub_questions or []
    if not sub_questions:
        return AdmissionCheck("R17_sub_question_completeness", True, "review", "")

    incomplete = []
    for sub in sub_questions:
        qno = getattr(sub, "qno", None)
        stem = getattr(sub, "stem", None)
        stem_line_ids = getattr(sub, "stem_line_ids", None)
        answer = getattr(sub, "answer", None)
        options = getattr(sub, "options", None)
        qtype = getattr(sub, "question_type", None)

        if not qno:
            incomplete.append("无qno")
            continue

        has_stem = bool(stem and stem.strip()) or bool(stem_line_ids)
        has_answer = bool(answer and answer.strip())

        if not has_stem:
            incomplete.append(f"Q{qno}:无stem")
        if not has_answer:
            incomplete.append(f"Q{qno}:无answer")

        # 选择题子题必须有选项
        if qtype in ("single_choice", "multiple_choice") and not options:
            incomplete.append(f"Q{qno}:选择题无options")

    if incomplete:
        return AdmissionCheck(
            "R17_sub_question_completeness",
            False,
            "review",
            f"子题不完整: {'; '.join(incomplete[:3])}",
        )

    return AdmissionCheck("R17_sub_question_completeness", True, "review", "")


# ── 辅助函数 ──────────────────────────────────────────────────────


def _text_overlap_ratio(text_a: str, text_b: str) -> float:
    """计算两段文本的序列级相似度（0.0-1.0）。

    使用 SequenceMatcher 做序列对比，而非字符集重叠。
    对顺序敏感：'a=3,b=4' vs 'a=4,b=3' 会得到较低分数。
    """
    if not text_a or not text_b:
        return 0.0
    return SequenceMatcher(None, text_a, text_b).ratio()


def _slice_by_line_ids(line_ids: list[str], l1_lines: list[dict]) -> str:
    """从 L1 行列表中按行号切片，返回拼接文本。"""
    if not line_ids or not l1_lines:
        return ""

    line_map = {}
    for line in l1_lines:
        lid = line.get("id", "")
        if lid:
            line_map[lid] = line.get("text", "")

    parts = []
    for lid in line_ids:
        text = line_map.get(lid, "")
        if text:
            parts.append(text)
    return "\n".join(parts)


# ── 主入口 ──────────────────────────────────────────────────────


def admit_question(
    sq: SlicedQuestion,
    l1_lines: list[dict] | None = None,
    question_images: list[dict] | None = None,
) -> AdmissionDecision:
    """逐题入库门禁决策。

    Args:
        sq: 切片后的题目
        l1_lines: L1 原文行列表（用于 R08 行号一致性校验），可为 None

    Returns:
        AdmissionDecision，包含 decision (approve/review/reject) 和所有检查结果
    """
    decision = AdmissionDecision()

    # ── 第一轮：硬性 reject 规则 ──────────────────────────────────
    reject_checks = [
        _check_R01_stem_non_empty(sq),
        _check_R02_no_stem_options_in_answer(sq),
        _check_R03_stem_length_sane(sq),
        _check_R04_options_count_sane(sq),
        _check_R08_slice_consistency(sq, l1_lines),
        _check_R12_answer_content_sane(sq),
    ]

    for check in reject_checks:
        decision.add_check(check)
        if not check.passed and check.severity == "reject":
            decision.decision = "reject"
            decision.reject_reason = check.rule
            return decision

    # ── 第二轮：review 规则 ──────────────────────────────────────
    review_checks = [
        _check_R05_choice_labels_match(sq),
        _check_R06_answer_provenance_trusted(sq),
        _check_R07_no_duplicate_answer_sources(sq),
        _check_R09_explanation_not_answer(sq),
        _check_R10_explanation_length_sane(sq),
        _check_R13_composite_answer_format(sq),
        _check_R14_shared_material_exists(sq),
        _check_R15_word_bank_for_cloze(sq),
        _check_R16_images_have_metadata(sq, question_images),
        _check_R17_sub_question_completeness(sq),
    ]

    review_failing_rules: list[str] = []
    for check in review_checks:
        decision.add_check(check)
        if not check.passed and check.severity == "review":
            if decision.decision != "reject":
                decision.decision = "review"
                review_failing_rules.append(check.rule)

    if review_failing_rules:
        decision.review_reason = "; ".join(review_failing_rules)

    # ── 第三轮：metadata 规则（不改变决策）───────────────────────
    metadata_checks = [
        _check_R11_metadata_completeness(sq),
    ]

    for check in metadata_checks:
        decision.add_check(check)

    # ── 最终决策 ──────────────────────────────────────────────────
    if decision.decision == "reject":
        decision.reject_reason = decision.reject_reason or "unknown_reject"
    elif decision.decision == "review":
        decision.review_reason = decision.review_reason or "unknown_review"
    else:
        decision.decision = "approve"
        decision.reject_reason = None
        decision.review_reason = None

    return decision

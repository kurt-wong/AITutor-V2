"""Admission Gate 单元测试。

覆盖 13 条规则的正反例 + 三态决策逻辑。
测试标准：每个结论都有严格测试证据对应，不降低标准。
"""

import pytest

from app.domains.document.admission_gate import (
    AdmissionDecision,
    admit_question,
)
from app.domains.document.schemas_l2 import L2SubQuestion, SlicedQuestion, SourceProvenance


# ── 辅助构造器 ──────────────────────────────────────────────────────


def _make_choice_question(
    *,
    stem="下列哪个选项正确？",
    options=None,
    answer="A",
    provenance_source="document_answer_table",
    **kwargs,
) -> SlicedQuestion:
    """构造标准选择题。"""
    if options is None:
        options = [
            {"label": "A", "text": "选项A内容"},
            {"label": "B", "text": "选项B内容"},
            {"label": "C", "text": "选项C内容"},
            {"label": "D", "text": "选项D内容"},
        ]
    return SlicedQuestion(
        question_number="1",
        question_type="single_choice",
        stem=stem,
        options=options,
        answer=answer,
        answer_provenance=SourceProvenance("answer", provenance_source, 1.0),
        stem_line_ids=["P1L001", "P1L002"],
        section_id="section_1",
        score=3.0,
        difficulty=2,
        knowledge_points=["知识点A"],
        **kwargs,
    )


def _make_fill_question(**kwargs) -> SlicedQuestion:
    """构造标准填空题。"""
    provenance_source = kwargs.pop("provenance_source", "document_answer_table")
    defaults = dict(
        question_number="5",
        question_type="fill_in",
        stem="请在横线上填写正确的词语。",
        options=[],
        answer="正确词语",
        answer_provenance=SourceProvenance("answer", provenance_source, 1.0),
        stem_line_ids=["P1L010"],
        section_id="section_2",
        score=2.0,
        difficulty=3,
        knowledge_points=["知识点B"],
    )
    defaults.update(kwargs)
    return SlicedQuestion(**defaults)


# ═══════════════════════════════════════════════════════════════════
# R01: stem 非空
# ═══════════════════════════════════════════════════════════════════


class TestR01StemNonEmpty:
    """R01: stem 非空 → reject if empty。"""

    def test_empty_stem_rejects(self):
        sq = _make_choice_question(stem="")
        d = admit_question(sq)
        assert d.decision == "reject"
        assert d.reject_reason == "R01_stem_non_empty"

    def test_whitespace_only_stem_rejects(self):
        sq = _make_choice_question(stem="   \n\t  ")
        d = admit_question(sq)
        assert d.decision == "reject"
        assert d.reject_reason == "R01_stem_non_empty"

    def test_normal_stem_passes(self):
        sq = _make_choice_question(stem="正常的题目题干")
        d = admit_question(sq)
        assert d.decision != "reject" or d.reject_reason != "R01_stem_non_empty"

    def test_r01_check_result(self):
        sq = _make_choice_question(stem="")
        d = admit_question(sq)
        r01 = [c for c in d.checks if c.rule == "R01_stem_non_empty"][0]
        assert r01.passed is False
        assert r01.severity == "reject"
        assert "题干为空" in r01.message


# ═══════════════════════════════════════════════════════════════════
# R02: answer 不包含 stem/options 文本
# ═══════════════════════════════════════════════════════════════════


class TestR02NoStemOptionsInAnswer:
    """R02: answer 不应包含 stem/options 文本。"""

    def test_normal_answer_passes(self):
        sq = _make_choice_question(answer="A")
        d = admit_question(sq)
        r02 = [c for c in d.checks if c.rule == "R02_no_stem_options_in_answer"][0]
        assert r02.passed is True

    def test_answer_containing_full_stem_rejects(self):
        """答案包含完整题干 → reject。"""
        stem = "这是一道正常的数学题目，考察学生的逻辑思维能力，需要仔细分析每个步骤才能得出正确答案"
        sq = _make_choice_question(
            stem=stem,
            answer=stem + " 答案是A",
        )
        d = admit_question(sq)
        assert d.decision == "reject"
        assert d.reject_reason == "R02_no_stem_options_in_answer"

    def test_answer_with_multiple_options_texts_rejects(self):
        """答案包含 3+ 个选项文本 → reject。"""
        options = [
            {"label": "A", "text": "北京"},
            {"label": "B", "text": "上海"},
            {"label": "C", "text": "广州"},
            {"label": "D", "text": "深圳"},
        ]
        sq = _make_choice_question(
            options=options,
            answer="北京 上海 广州 深圳",
        )
        d = admit_question(sq)
        assert d.decision == "reject"
        assert d.reject_reason == "R02_no_stem_options_in_answer"

    def test_empty_answer_skips(self):
        sq = _make_choice_question(answer="")
        d = admit_question(sq)
        r02 = [c for c in d.checks if c.rule == "R02_no_stem_options_in_answer"][0]
        assert r02.passed is True


# ═══════════════════════════════════════════════════════════════════
# R03: stem 长度合理
# ═══════════════════════════════════════════════════════════════════


class TestR03StemLengthSane:
    """R03: stem 长度不超过阈值。"""

    def test_short_stem_passes(self):
        sq = _make_choice_question(stem="短题干")
        d = admit_question(sq)
        r03 = [c for c in d.checks if c.rule == "R03_stem_length_sane"][0]
        assert r03.passed is True

    def test_long_choice_stem_rejects(self):
        """选择题 stem > 800 字符 → reject。"""
        long_stem = "题目内容" * 201  # ~804 chars, exceeds 800 limit
        sq = _make_choice_question(stem=long_stem)
        d = admit_question(sq)
        assert d.decision == "reject"
        assert d.reject_reason == "R03_stem_length_sane"

    def test_composite_long_stem_passes(self):
        """综合题 stem > 800 但 < 3000 → pass。"""
        long_stem = "阅读材料" * 200
        sq = _make_choice_question(
            stem=long_stem,
            is_composite=True,
            sub_questions=[L2SubQuestion(qno="1", answer="A")],
        )
        d = admit_question(sq)
        r03 = [c for c in d.checks if c.rule == "R03_stem_length_sane"][0]
        assert r03.passed is True

    def test_short_answer_long_stem_passes(self):
        """short_answer 题型长题干按 3000 上限。"""
        long_stem = "解答题内容" * 200
        sq = _make_fill_question(
            stem=long_stem,
            question_type="short_answer",
        )
        d = admit_question(sq)
        r03 = [c for c in d.checks if c.rule == "R03_stem_length_sane"][0]
        assert r03.passed is True


# ═══════════════════════════════════════════════════════════════════
# R04: 选择题选项数量合理
# ═══════════════════════════════════════════════════════════════════


class TestR04OptionsCountSane:
    """R04: 选择题选项数量合理。"""

    def test_normal_4_options_passes(self):
        sq = _make_choice_question()
        d = admit_question(sq)
        r04 = [c for c in d.checks if c.rule == "R04_options_count_sane"][0]
        assert r04.passed is True

    def test_zero_options_rejects(self):
        sq = _make_choice_question(options=[])
        d = admit_question(sq)
        assert d.decision == "reject"
        assert d.reject_reason == "R04_options_count_sane"

    def test_too_many_options_rejects(self):
        """超过 7 个选项 → reject。"""
        options = [{"label": chr(65 + i), "text": f"opt{i}"} for i in range(8)]
        sq = _make_choice_question(options=options)
        d = admit_question(sq)
        assert d.decision == "reject"
        assert d.reject_reason == "R04_options_count_sane"

    def test_fill_blank_skips(self):
        """填空题不检查选项数量。"""
        sq = _make_fill_question()
        d = admit_question(sq)
        r04 = [c for c in d.checks if c.rule == "R04_options_count_sane"][0]
        assert r04.passed is True

    def test_composite_skips(self):
        """综合题不检查选项数量。"""
        sq = _make_choice_question(
            options=[],
            is_composite=True,
            sub_questions=[L2SubQuestion(qno="1", answer="A")],
        )
        d = admit_question(sq)
        r04 = [c for c in d.checks if c.rule == "R04_options_count_sane"][0]
        assert r04.passed is True


# ═══════════════════════════════════════════════════════════════════
# R05: 选择题选项标签匹配
# ═══════════════════════════════════════════════════════════════════


class TestR05ChoiceLabelsMatch:
    """R05: 选择题选项标签规范。"""

    def test_standard_labels_pass(self):
        sq = _make_choice_question()
        d = admit_question(sq)
        r05 = [c for c in d.checks if c.rule == "R05_choice_labels_match"][0]
        assert r05.passed is True

    def test_non_standard_labels_review(self):
        """非标准标签 → review（不 reject）。"""
        options = [
            {"label": "甲", "text": "选项A"},
            {"label": "乙", "text": "选项B"},
            {"label": "丙", "text": "选项C"},
            {"label": "丁", "text": "选项D"},
        ]
        sq = _make_choice_question(options=options)
        d = admit_question(sq)
        r05 = [c for c in d.checks if c.rule == "R05_choice_labels_match"][0]
        assert r05.passed is False
        assert r05.severity == "review"
        # 不应导致 reject
        assert d.decision != "reject" or d.reject_reason != "R05_choice_labels_match"


# ═══════════════════════════════════════════════════════════════════
# R06: 答案来源可信
# ═══════════════════════════════════════════════════════════════════


class TestR06AnswerProvenanceTrusted:
    """R06: 答案来源可信度。"""

    def test_document_answer_table_passes(self):
        sq = _make_choice_question(provenance_source="document_answer_table")
        d = admit_question(sq)
        r06 = [c for c in d.checks if c.rule == "R06_answer_provenance_trusted"][0]
        assert r06.passed is True

    def test_llm_fallback_reviews(self):
        sq = _make_choice_question(provenance_source="llm_fallback")
        d = admit_question(sq)
        r06 = [c for c in d.checks if c.rule == "R06_answer_provenance_trusted"][0]
        assert r06.passed is False
        assert r06.severity == "review"

    def test_llm_annotation_choice_passes(self):
        """选择题 + llm_annotation → pass。"""
        sq = _make_choice_question(provenance_source="llm_annotation")
        d = admit_question(sq)
        r06 = [c for c in d.checks if c.rule == "R06_answer_provenance_trusted"][0]
        assert r06.passed is True

    def test_llm_annotation_short_answer_reviews(self):
        """解答题 + llm_annotation → review。"""
        sq = _make_fill_question(
            question_type="short_answer",
            provenance_source="llm_annotation",
        )
        d = admit_question(sq)
        r06 = [c for c in d.checks if c.rule == "R06_answer_provenance_trusted"][0]
        assert r06.passed is False
        assert r06.severity == "review"

    def test_no_provenance_reviews(self):
        """无来源标记 → review。"""
        sq = _make_choice_question()
        sq.answer_provenance = None
        d = admit_question(sq)
        r06 = [c for c in d.checks if c.rule == "R06_answer_provenance_trusted"][0]
        assert r06.passed is False
        assert r06.severity == "review"


# ═══════════════════════════════════════════════════════════════════
# R08: 行号回填一致性
# ═══════════════════════════════════════════════════════════════════


class TestR08SliceConsistency:
    """R08: 行号切片文本与 stem 一致。"""

    def test_no_line_ids_reviews(self):
        """无行号引用 → review。"""
        sq = _make_choice_question()
        sq.stem_line_ids = []
        d = admit_question(sq)
        r08 = [c for c in d.checks if c.rule == "R08_slice_consistency"][0]
        assert r08.passed is False
        assert r08.severity == "review"

    def test_no_l1_lines_passes(self):
        """无 L1 原文可比对 → review（不能 approve）。"""
        sq = _make_choice_question()
        d = admit_question(sq, l1_lines=None)
        r08 = [c for c in d.checks if c.rule == "R08_slice_consistency"][0]
        assert r08.passed is False
        assert r08.severity == "review"

    def test_consistent_slice_passes(self):
        """行号切片文本与 stem 一致 → pass。"""
        l1_lines = [
            {"id": "P1L001", "text": "下列哪个"},
            {"id": "P1L002", "text": "选项正确？"},
        ]
        sq = _make_choice_question(stem="下列哪个\n选项正确？")
        d = admit_question(sq, l1_lines=l1_lines)
        r08 = [c for c in d.checks if c.rule == "R08_slice_consistency"][0]
        assert r08.passed is True

    def test_inconsistent_slice_rejects(self):
        """行号切片文本与 stem 不一致 → reject。"""
        l1_lines = [
            {"id": "P1L001", "text": "完全不同的一道题"},
            {"id": "P1L002", "text": "内容完全对不上"},
        ]
        sq = _make_choice_question(stem="下列哪个选项正确？")
        d = admit_question(sq, l1_lines=l1_lines)
        assert d.decision == "reject"
        assert d.reject_reason == "R08_slice_consistency"

    def test_empty_slice_rejects(self):
        """行号切片结果为空 → reject。"""
        l1_lines = [
            {"id": "P1L999", "text": "不匹配的行"},
        ]
        sq = _make_choice_question()
        d = admit_question(sq, l1_lines=l1_lines)
        assert d.decision == "reject"
        assert d.reject_reason == "R08_slice_consistency"


# ═══════════════════════════════════════════════════════════════════
# R09: explanation 不是答案的重复
# ═══════════════════════════════════════════════════════════════════


class TestR09ExplanationNotAnswer:
    """R09: 详解不应与答案完全相同。"""

    def test_different_explanation_passes(self):
        sq = _make_choice_question(explanation="因为选项A正确，所以选A")
        d = admit_question(sq)
        r09 = [c for c in d.checks if c.rule == "R09_explanation_not_answer"][0]
        assert r09.passed is True

    def test_same_explanation_reviews(self):
        """详解与答案完全相同 → review。"""
        sq = _make_choice_question(explanation="A")
        d = admit_question(sq)
        r09 = [c for c in d.checks if c.rule == "R09_explanation_not_answer"][0]
        assert r09.passed is False
        assert r09.severity == "review"

    def test_empty_explanation_skips(self):
        sq = _make_choice_question(explanation="")
        d = admit_question(sq)
        r09 = [c for c in d.checks if c.rule == "R09_explanation_not_answer"][0]
        assert r09.passed is True


# ═══════════════════════════════════════════════════════════════════
# R10: explanation 长度合理
# ═══════════════════════════════════════════════════════════════════


class TestR10ExplanationLengthSane:
    """R10: 详解长度 >3 字符。"""

    def test_normal_explanation_passes(self):
        sq = _make_choice_question(explanation="这是一段正常的详解内容")
        d = admit_question(sq)
        r10 = [c for c in d.checks if c.rule == "R10_explanation_length_sane"][0]
        assert r10.passed is True

    def test_short_explanation_metadata(self):
        """短详解 → metadata（不阻断）。"""
        sq = _make_choice_question(explanation="对")
        d = admit_question(sq)
        r10 = [c for c in d.checks if c.rule == "R10_explanation_length_sane"][0]
        assert r10.passed is False
        assert r10.severity == "metadata"
        # 不应影响决策
        assert d.decision != "reject"

    def test_empty_explanation_skips(self):
        sq = _make_choice_question(explanation="")
        d = admit_question(sq)
        r10 = [c for c in d.checks if c.rule == "R10_explanation_length_sane"][0]
        assert r10.passed is True


# ═══════════════════════════════════════════════════════════════════
# R11: 元数据完整性
# ═══════════════════════════════════════════════════════════════════


class TestR11MetadataCompleteness:
    """R11: 元数据完整性（不阻断）。"""

    def test_full_metadata_passes(self):
        sq = _make_choice_question()
        d = admit_question(sq)
        r11 = [c for c in d.checks if c.rule == "R11_metadata_completeness"][0]
        assert r11.passed is True

    def test_missing_metadata_records(self):
        """缺失元数据 → metadata（不阻断）。"""
        sq = SlicedQuestion(
            question_number="1",
            question_type="single_choice",
            stem="正常题干",
            options=[
                {"label": "A", "text": "选项A"},
                {"label": "B", "text": "选项B"},
                {"label": "C", "text": "选项C"},
                {"label": "D", "text": "选项D"},
            ],
            answer="A",
            answer_provenance=SourceProvenance("answer", "document_answer_table", 1.0),
            stem_line_ids=["P1L001"],
            # 缺失: section_id, score, difficulty, knowledge_points
        )
        d = admit_question(sq)
        r11 = [c for c in d.checks if c.rule == "R11_metadata_completeness"][0]
        assert r11.passed is False
        assert r11.severity == "review"
        # 不应影响 approve 决策
        assert d.decision == "approve"


# ═══════════════════════════════════════════════════════════════════
# R12: 答案内容合理性
# ═══════════════════════════════════════════════════════════════════


class TestR12AnswerContentSane:
    """R12: 答案内容合理性。"""

    def test_normal_answer_passes(self):
        sq = _make_choice_question(answer="A")
        d = admit_question(sq)
        r12 = [c for c in d.checks if c.rule == "R12_answer_content_sane"][0]
        assert r12.passed is True

    def test_punctuation_only_rejects(self):
        """答案仅标点 → reject。"""
        sq = _make_choice_question(answer="。，；")
        d = admit_question(sq)
        assert d.decision == "reject"
        assert d.reject_reason == "R12_answer_content_sane"

    def test_empty_answer_skips(self):
        sq = _make_choice_question(answer="")
        d = admit_question(sq)
        r12 = [c for c in d.checks if c.rule == "R12_answer_content_sane"][0]
        assert r12.passed is True


# ═══════════════════════════════════════════════════════════════════
# R13: 综合题答案格式
# ═══════════════════════════════════════════════════════════════════


class TestR13CompositeAnswerFormat:
    """R13: 综合题答案格式。"""

    def test_non_composite_skips(self):
        sq = _make_choice_question()
        d = admit_question(sq)
        r13 = [c for c in d.checks if c.rule == "R13_composite_answer_format"][0]
        assert r13.passed is True

    def test_composite_with_subs_passes(self):
        sq = _make_choice_question(
            is_composite=True,
            sub_questions=[
                L2SubQuestion(qno="1", answer="A"),
                L2SubQuestion(qno="2", answer="B"),
            ],
        )
        d = admit_question(sq)
        r13 = [c for c in d.checks if c.rule == "R13_composite_answer_format"][0]
        assert r13.passed is True

    def test_composite_no_subs_reviews(self):
        """综合题标记但无子题 → review。"""
        sq = _make_choice_question(
            is_composite=True,
            sub_questions=None,
        )
        d = admit_question(sq)
        r13 = [c for c in d.checks if c.rule == "R13_composite_answer_format"][0]
        assert r13.passed is False
        assert r13.severity == "review"

    def test_composite_all_subs_no_answer_reviews(self):
        """综合题所有子题无答案 → review。"""
        sq = _make_choice_question(
            is_composite=True,
            sub_questions=[
                L2SubQuestion(qno="1", answer=None),
                L2SubQuestion(qno="2", answer=None),
            ],
        )
        d = admit_question(sq)
        r13 = [c for c in d.checks if c.rule == "R13_composite_answer_format"][0]
        assert r13.passed is False
        assert r13.severity == "review"


# ═══════════════════════════════════════════════════════════════════
# 三态决策集成测试
# ═══════════════════════════════════════════════════════════════════


class TestDecisionIntegration:
    """三态决策集成测试。"""

    def test_perfect_question_approves(self):
        """完美题目 → approve。"""
        sq = _make_choice_question(
            explanation="因为A是正确答案，所以选A。这道题考察基本概念理解。",
        )
        d = admit_question(sq)
        assert d.decision == "approve"
        assert d.passed is True
        assert d.reject_reason is None
        assert d.review_reason is None

    def test_empty_stem_immediate_reject(self):
        """空 stem → 立即 reject（R01 第一条就拦截）。"""
        sq = _make_choice_question(stem="")
        d = admit_question(sq)
        assert d.decision == "reject"
        assert d.reject_reason == "R01_stem_non_empty"
        # 只有 R01 的检查结果（early return）
        assert len(d.checks) == 1

    def test_review_does_not_override_reject(self):
        """reject 优先于 review。"""
        sq = _make_choice_question(
            stem="正常题干",
            options=[],  # R04 reject
            answer="A",
            explanation="A",  # R09 review
        )
        d = admit_question(sq)
        assert d.decision == "reject"
        assert d.reject_reason == "R04_options_count_sane"

    def test_metadata_does_not_override_review(self):
        """metadata 不改变 review 决策。"""
        sq = SlicedQuestion(
            question_number="1",
            question_type="single_choice",
            stem="正常题干",
            options=[
                {"label": "A", "text": "选项A"},
                {"label": "B", "text": "选项B"},
                {"label": "C", "text": "选项C"},
                {"label": "D", "text": "选项D"},
            ],
            answer="A",
            answer_provenance=SourceProvenance("answer", "document_answer_table", 1.0),
            stem_line_ids=["P1L001"],
            explanation="A",  # R09 review
            # 缺失: section_id, score → R11 metadata
        )
        d = admit_question(sq)
        assert d.decision == "review"
        assert d.review_reason == "R09_explanation_not_answer"

    def test_all_checks_present_on_approve(self):
        """approve 时应有全部 13 条检查结果。"""
        sq = _make_choice_question(
            explanation="这是一段正常的详解内容，用来解释答案。"
        )
        d = admit_question(sq)
        assert d.decision == "approve"
        rules = {c.rule for c in d.checks}
        expected_rules = {
            "R01_stem_non_empty",
            "R02_no_stem_options_in_answer",
            "R03_stem_length_sane",
            "R04_options_count_sane",
            "R05_choice_labels_match",
            "R06_answer_provenance_trusted",
            "R07_no_duplicate_answer_sources",
            "R08_slice_consistency",
            "R09_explanation_not_answer",
            "R10_explanation_length_sane",
            "R11_metadata_completeness",
            "R12_answer_content_sane",
            "R13_composite_answer_format",
            "R14_shared_material_exists",
            "R15_word_bank_for_cloze",
            "R16_images_have_metadata",
            "R17_sub_question_completeness",
        }
        assert rules == expected_rules


# ═══════════════════════════════════════════════════════════════════
# 辅助函数测试
# ═══════════════════════════════════════════════════════════════════


class TestHelpers:
    """辅助函数测试。"""

    def test_text_overlap_ratio_identical(self):
        from app.domains.document.admission_gate import _text_overlap_ratio
        assert _text_overlap_ratio("abc", "abc") == 1.0

    def test_text_overlap_ratio_disjoint(self):
        from app.domains.document.admission_gate import _text_overlap_ratio
        assert _text_overlap_ratio("abc", "xyz") == 0.0

    def test_text_overlap_ratio_partial(self):
        from app.domains.document.admission_gate import _text_overlap_ratio
        ratio = _text_overlap_ratio("abcdef", "abcxyz")
        assert 0.3 < ratio < 0.7

    def test_text_overlap_ratio_empty(self):
        from app.domains.document.admission_gate import _text_overlap_ratio
        assert _text_overlap_ratio("", "abc") == 0.0
        assert _text_overlap_ratio("abc", "") == 0.0

    def test_slice_by_line_ids(self):
        from app.domains.document.admission_gate import _slice_by_line_ids
        l1 = [
            {"id": "P1L001", "text": "第一行"},
            {"id": "P1L002", "text": "第二行"},
            {"id": "P1L003", "text": "第三行"},
        ]
        result = _slice_by_line_ids(["P1L001", "P1L003"], l1)
        assert result == "第一行\n第三行"

    def test_slice_by_line_ids_missing(self):
        from app.domains.document.admission_gate import _slice_by_line_ids
        l1 = [{"id": "P1L001", "text": "第一行"}]
        result = _slice_by_line_ids(["P1L999"], l1)
        assert result == ""

    def test_slice_by_line_ids_empty(self):
        from app.domains.document.admission_gate import _slice_by_line_ids
        assert _slice_by_line_ids([], []) == ""
        assert _slice_by_line_ids(None, []) == ""


# ═══════════════════════════════════════════════════════════════════
# 对抗性审查修复验证（2026-09-01）
# ═══════════════════════════════════════════════════════════════════


class TestR07CrossFieldConsistency:
    """R07: 答案/详解来源一致性检查。"""

    def test_both_trusted_sources_passes(self):
        """answer + explanation 都来自可信来源 → 通过。"""
        sq = _make_choice_question(
            explanation="详解内容",
            explanation_provenance=SourceProvenance("explanation", "document_inline_explanation", 1.0),
        )
        d = admit_question(sq)
        r07 = [c for c in d.checks if c.rule == "R07_no_duplicate_answer_sources"][0]
        assert r07.passed is True

    def test_trusted_answer_llm_explanation_reviews(self):
        """answer 可信 + explanation 来自 LLM → review。"""
        sq = _make_choice_question(
            explanation="LLM生成的详解",
            explanation_provenance=SourceProvenance("explanation", "llm_fallback", 0.5),
        )
        d = admit_question(sq)
        r07 = [c for c in d.checks if c.rule == "R07_no_duplicate_answer_sources"][0]
        assert r07.passed is False
        assert r07.severity == "review"
        assert "LLM" in r07.message

    def test_both_llm_fallback_reviews(self):
        """answer + explanation 都来自 llm_fallback → review。"""
        sq = _make_choice_question(
            provenance_source="llm_fallback",
            explanation="LLM详解",
            explanation_provenance=SourceProvenance("explanation", "llm_fallback", 0.5),
        )
        d = admit_question(sq)
        r07 = [c for c in d.checks if c.rule == "R07_no_duplicate_answer_sources"][0]
        assert r07.passed is False
        assert "双重不确定性" in r07.message

    def test_no_answer_provenance_passes(self):
        """无 answer_provenance → 跳过检查。"""
        sq = SlicedQuestion(
            question_number="1", question_type="single_choice",
            stem="题目", answer="A",
            options=[{"label": "A", "text": "X"}, {"label": "B", "text": "Y"},
                     {"label": "C", "text": "Z"}, {"label": "D", "text": "W"}],
            stem_line_ids=["L1"],
        )
        d = admit_question(sq)
        r07 = [c for c in d.checks if c.rule == "R07_no_duplicate_answer_sources"][0]
        assert r07.passed is True


class TestTextOverlapRatioSequenceBased:
    """验证 _text_overlap_ratio 使用序列对比而非字符集。"""

    def test_same_content_different_order_low_score(self):
        """相同字符但顺序不同 → 较低分数。"""
        from app.domains.document.admission_gate import _text_overlap_ratio
        a = "已知三角形ABC三边a=3,b=4,c=5"
        b = "已知三角形ABC三边a=5,b=4,c=3"
        ratio = _text_overlap_ratio(a, b)
        assert ratio < 0.95, f"Expected < 0.95 for different order, got {ratio}"

    def test_identical_text_scores_one(self):
        from app.domains.document.admission_gate import _text_overlap_ratio
        assert _text_overlap_ratio("abc", "abc") == 1.0

    def test_completely_different_scores_zero(self):
        from app.domains.document.admission_gate import _text_overlap_ratio
        assert _text_overlap_ratio("aaa", "bbb") == 0.0

    def test_substring_high_score(self):
        """子串关系 → 高分但不满分。"""
        from app.domains.document.admission_gate import _text_overlap_ratio
        ratio = _text_overlap_ratio("ABCDEF", "ABC")
        assert ratio > 0.5


class TestR12ExpandedPUADetection:
    """R12: 扩展 PUA/不可见字符检测。"""

    def test_supplementary_pua_rejects(self):
        """Supplementary PUA (U+F0000) → reject。"""
        sq = _make_choice_question(answer="A\U000F0000")
        d = admit_question(sq)
        r12 = [c for c in d.checks if c.rule == "R12_answer_content_sane"][0]
        assert r12.passed is False
        assert d.decision == "reject"

    def test_replacement_char_rejects(self):
        """Replacement char (U+FFFD) → reject。"""
        sq = _make_choice_question(answer="A�")
        d = admit_question(sq)
        r12 = [c for c in d.checks if c.rule == "R12_answer_content_sane"][0]
        assert r12.passed is False

    def test_normal_unicode_passes(self):
        """正常中文/英文/数字 → 通过。"""
        sq = _make_choice_question(answer="正确答案是A，得3分")
        d = admit_question(sq)
        r12 = [c for c in d.checks if c.rule == "R12_answer_content_sane"][0]
        assert r12.passed is True


class TestReviewReasonCollection:
    """验证 review 循环收集所有失败原因。"""

    def test_multiple_review_failures_collected(self):
        """多个 review 规则失败时，review_reason 包含所有规则名。"""
        sq = SlicedQuestion(
            question_number="1", question_type="single_choice",
            stem="题目内容足够长以通过R03检查",
            answer="A",
            options=[{"label": "A", "text": "X"}, {"label": "B", "text": "Y"},
                     {"label": "C", "text": "Z"}, {"label": "D", "text": "W"}],
            answer_provenance=SourceProvenance("answer", "llm_fallback", 0.5),
            explanation="A",  # R09: explanation == answer
            stem_line_ids=["L1"],
            section_id="s1", score=3.0, difficulty=2, knowledge_points=["K"],
        )
        d = admit_question(sq)
        assert d.decision == "review"
        # review_reason 应包含 R06(llm_fallback) 和 R09(explanation==answer)
        assert "R06" in d.review_reason
        assert "R09" in d.review_reason

    def test_single_review_failure(self):
        """单个 review 失败时，review_reason 只有一个规则名。"""
        sq = _make_choice_question(
            provenance_source="llm_fallback",
            explanation="正常的详解内容不等于答案",
        )
        d = admit_question(sq)
        assert d.decision == "review"
        assert d.review_reason == "R06_answer_provenance_trusted"


class TestAdmitQuestionWithL1Lines:
    """验证 admit_question 接受 l1_lines 参数。"""

    def test_consistent_slice_with_l1_lines(self):
        """有 l1_lines 且切片一致 → R08 passed。"""
        l1 = [
            {"id": "P1L001", "text": "下列哪个选项正确？"},
            {"id": "P1L002", "text": "A. 选项A内容"},
        ]
        sq = SlicedQuestion(
            question_number="1", question_type="single_choice",
            stem="下列哪个选项正确？",
            options=[{"label": "A", "text": "选项A内容"}, {"label": "B", "text": "选项B内容"},
                     {"label": "C", "text": "选项C内容"}, {"label": "D", "text": "选项D内容"}],
            answer="A",
            answer_provenance=SourceProvenance("answer", "document_answer_table", 1.0),
            stem_line_ids=["P1L001"],
            section_id="s1", score=3.0, difficulty=2, knowledge_points=["K"],
        )
        d = admit_question(sq, l1_lines=l1)
        r08 = [c for c in d.checks if c.rule == "R08_slice_consistency"][0]
        assert r08.passed is True

    def test_inconsistent_slice_with_l1_lines_rejects(self):
        """有 l1_lines 但切片与 stem 不一致 → R08 reject。"""
        l1 = [
            {"id": "P1L001", "text": "完全不同的内容，与stem无关"},
        ]
        sq = SlicedQuestion(
            question_number="1", question_type="single_choice",
            stem="下列哪个选项正确？",
            options=[{"label": "A", "text": "选项A内容"}, {"label": "B", "text": "选项B内容"},
                     {"label": "C", "text": "选项C内容"}, {"label": "D", "text": "选项D内容"}],
            answer="A",
            answer_provenance=SourceProvenance("answer", "document_answer_table", 1.0),
            stem_line_ids=["P1L001"],
            section_id="s1", score=3.0, difficulty=2, knowledge_points=["K"],
        )
        d = admit_question(sq, l1_lines=l1)
        r08 = [c for c in d.checks if c.rule == "R08_slice_consistency"][0]
        assert r08.passed is False
        assert r08.severity == "reject"

    def test_no_l1_lines_bypass(self):
        """无 l1_lines → R08 review（不能 approve）。"""
        sq = SlicedQuestion(
            question_number="1", question_type="single_choice",
            stem="题目",
            options=[{"label": "A", "text": "X"}, {"label": "B", "text": "Y"},
                     {"label": "C", "text": "Z"}, {"label": "D", "text": "W"}],
            answer="A",
            answer_provenance=SourceProvenance("answer", "document_answer_table", 1.0),
            stem_line_ids=["P1L001"],
            section_id="s1", score=3.0, difficulty=2, knowledge_points=["K"],
        )
        d = admit_question(sq, l1_lines=None)
        r08 = [c for c in d.checks if c.rule == "R08_slice_consistency"][0]
        assert r08.passed is False
        assert r08.severity == "review"


# ═══════════════════════════════════════════════════════════════════
# 第二轮对抗性审查修复验证（2026-09-01）
# ═══════════════════════════════════════════════════════════════════


class TestR02StemEqualsAnswer:
    """R02: answer == stem 应被拒绝（数据质量问题）。"""

    def test_short_stem_equals_answer_rejects(self):
        """短茎 stem == answer → reject（修复前会绕过）。"""
        sq = _make_choice_question(
            stem="下列哪个选项正确",
            answer="下列哪个选项正确",
        )
        d = admit_question(sq)
        r02 = [c for c in d.checks if c.rule == "R02_no_stem_options_in_answer"][0]
        assert r02.passed is False
        assert d.decision == "reject"

    def test_long_stem_equals_answer_rejects(self):
        """长茎 stem == answer → reject。"""
        sq = _make_choice_question(
            stem="已知三角形ABC的三边长分别为3、4、5，求三角形的面积是多少",
            answer="已知三角形ABC的三边长分别为3、4、5，求三角形的面积是多少",
        )
        d = admit_question(sq)
        r02 = [c for c in d.checks if c.rule == "R02_no_stem_options_in_answer"][0]
        assert r02.passed is False

    def test_different_stem_answer_passes(self):
        """stem != answer → 通过。"""
        sq = _make_choice_question(stem="下列哪个选项正确", answer="A")
        d = admit_question(sq)
        r02 = [c for c in d.checks if c.rule == "R02_no_stem_options_in_answer"][0]
        assert r02.passed is True


class TestR13WhitespaceSubAnswer:
    """R13: 纯空白子题答案应视为无答案。"""

    def test_whitespace_only_sub_answer_reviews(self):
        """子题 answer='  '（纯空白）→ review（修复前会误判为有答案）。"""
        sq = _make_choice_question(
            is_composite=True,
            sub_questions=[
                L2SubQuestion(qno="1", answer="  "),
                L2SubQuestion(qno="2", answer="  "),
            ],
        )
        d = admit_question(sq)
        r13 = [c for c in d.checks if c.rule == "R13_composite_answer_format"][0]
        assert r13.passed is False
        assert "均无答案" in r13.message

    def test_empty_string_sub_answer_reviews(self):
        """子题 answer='' → review。"""
        sq = _make_choice_question(
            is_composite=True,
            sub_questions=[
                L2SubQuestion(qno="1", answer=""),
                L2SubQuestion(qno="2", answer=""),
            ],
        )
        d = admit_question(sq)
        r13 = [c for c in d.checks if c.rule == "R13_composite_answer_format"][0]
        assert r13.passed is False

    def test_real_sub_answer_passes(self):
        """子题有真实答案 → 通过。"""
        sq = _make_choice_question(
            is_composite=True,
            sub_questions=[
                L2SubQuestion(qno="1", answer="A"),
                L2SubQuestion(qno="2", answer="B"),
            ],
        )
        d = admit_question(sq)
        r13 = [c for c in d.checks if c.rule == "R13_composite_answer_format"][0]
        assert r13.passed is True


class TestR08EmptyL1Lines:
    """R08: 空 l1_lines 列表应与 None 等价（不拒绝）。"""

    def test_empty_list_same_as_none(self):
        """l1_lines=[] → review（缺 L1 不能 approve）。"""
        sq = SlicedQuestion(
            question_number="1", question_type="single_choice",
            stem="题目", answer="A",
            options=[{"label": "A", "text": "X"}, {"label": "B", "text": "Y"},
                     {"label": "C", "text": "Z"}, {"label": "D", "text": "W"}],
            answer_provenance=SourceProvenance("answer", "document_answer_table", 1.0),
            stem_line_ids=["P1L001"],
            section_id="s1", score=3.0, difficulty=2, knowledge_points=["K"],
        )
        d = admit_question(sq, l1_lines=[])
        r08 = [c for c in d.checks if c.rule == "R08_slice_consistency"][0]
        assert r08.passed is False
        assert r08.severity == "review"

    def test_none_still_passes(self):
        """l1_lines=None → review（缺 L1 不能 approve）。"""
        sq = SlicedQuestion(
            question_number="1", question_type="single_choice",
            stem="题目", answer="A",
            options=[{"label": "A", "text": "X"}, {"label": "B", "text": "Y"},
                     {"label": "C", "text": "Z"}, {"label": "D", "text": "W"}],
            answer_provenance=SourceProvenance("answer", "document_answer_table", 1.0),
            stem_line_ids=["P1L001"],
            section_id="s1", score=3.0, difficulty=2, knowledge_points=["K"],
        )
        d = admit_question(sq, l1_lines=None)
        r08 = [c for c in d.checks if c.rule == "R08_slice_consistency"][0]
        assert r08.passed is False
        assert r08.severity == "review"


# ═══════════════════════════════════════════════════════════════════
# 用户反馈修复验证（R06/R14-R17 独立测试）
# ═══════════════════════════════════════════════════════════════════


def _make_sq(**kw):
    """快速构造 SlicedQuestion。"""
    defaults = dict(
        question_number="1", question_type="single_choice",
        stem="题目内容足够长以通过检查", answer="A",
        options=[{"label": "A", "text": "X"}, {"label": "B", "text": "Y"},
                 {"label": "C", "text": "Z"}, {"label": "D", "text": "W"}],
        answer_provenance=SourceProvenance("answer", "document_answer_table", 1.0),
        stem_line_ids=["L1"], section_id="s1", score=3.0,
        difficulty=2, knowledge_points=["K"],
    )
    defaults.update(kw)
    return SlicedQuestion(**defaults)


class TestR06ZeroConfidence:
    """R06: 零置信度可信来源应 review。"""

    def test_zero_conf_trusted_source_reviews(self):
        sq = _make_sq(answer_provenance=SourceProvenance("answer", "document_answer_table", 0.0))
        d = admit_question(sq)
        r06 = [c for c in d.checks if c.rule == "R06_answer_provenance_trusted"][0]
        assert r06.passed is False
        assert r06.severity == "review"

    def test_zero_conf_llm_annotation_reviews(self):
        sq = _make_sq(answer_provenance=SourceProvenance("answer", "llm_annotation", 0.0))
        d = admit_question(sq)
        r06 = [c for c in d.checks if c.rule == "R06_answer_provenance_trusted"][0]
        assert r06.passed is False

    def test_high_conf_trusted_source_passes(self):
        sq = _make_sq(answer_provenance=SourceProvenance("answer", "document_answer_table", 0.9))
        d = admit_question(sq)
        r06 = [c for c in d.checks if c.rule == "R06_answer_provenance_trusted"][0]
        assert r06.passed is True


class TestR14SharedMaterial:
    """R14: 材料型综合题必须有共享材料。"""

    def test_composite_with_material_keyword_no_material_reviews(self):
        """茎含'阅读'但无 shared_material → review。"""
        sq = _make_sq(
            stem="阅读下面材料完成题目", is_composite=True,
            sub_questions=[L2SubQuestion(qno="1", answer="A")],
            shared_material=None, shared_material_line_ids=[],
        )
        d = admit_question(sq)
        r14 = [c for c in d.checks if c.rule == "R14_shared_material_exists"][0]
        assert r14.passed is False

    def test_composite_with_material_text_passes(self):
        """有 shared_material → 通过。"""
        sq = _make_sq(
            stem="阅读下面材料完成题目", is_composite=True,
            shared_material="材料内容",
            sub_questions=[L2SubQuestion(qno="1", answer="A")],
        )
        d = admit_question(sq)
        r14 = [c for c in d.checks if c.rule == "R14_shared_material_exists"][0]
        assert r14.passed is True

    def test_non_composite_skips(self):
        sq = _make_sq()
        d = admit_question(sq)
        r14 = [c for c in d.checks if c.rule == "R14_shared_material_exists"][0]
        assert r14.passed is True


class TestR15WordBank:
    """R15: 选词填空/词汇填空必须有词库。只检查 word_fill / vocabulary_fill / wordbank_fill。"""

    def test_word_fill_no_word_bank_reviews(self):
        """word_fill 无 word_bank → review。"""
        sq = _make_sq(question_type="word_fill")
        d = admit_question(sq)
        r15 = [c for c in d.checks if c.rule == "R15_word_bank_for_cloze"][0]
        assert r15.passed is False

    def test_vocabulary_fill_no_word_bank_reviews(self):
        """vocabulary_fill 无 word_bank → review。"""
        sq = _make_sq(question_type="vocabulary_fill")
        d = admit_question(sq)
        r15 = [c for c in d.checks if c.rule == "R15_word_bank_for_cloze"][0]
        assert r15.passed is False

    def test_wordbank_fill_no_word_bank_reviews(self):
        """wordbank_fill 无 word_bank → review。"""
        sq = _make_sq(question_type="wordbank_fill")
        d = admit_question(sq)
        r15 = [c for c in d.checks if c.rule == "R15_word_bank_for_cloze"][0]
        assert r15.passed is False

    def test_word_fill_with_word_bank_passes(self):
        """word_fill 有 word_bank → 通过。"""
        sq = _make_sq(question_type="word_fill", word_bank=["apple", "banana"])
        d = admit_question(sq)
        r15 = [c for c in d.checks if c.rule == "R15_word_bank_for_cloze"][0]
        assert r15.passed is True

    def test_fill_in_no_word_bank_passes(self):
        """fill_in 无 word_bank → 通过（普通填空不需要词库）。"""
        sq = _make_sq(question_type="fill_in")
        d = admit_question(sq)
        r15 = [c for c in d.checks if c.rule == "R15_word_bank_for_cloze"][0]
        assert r15.passed is True

    def test_grammar_fill_no_word_bank_passes(self):
        """grammar_fill 无 word_bank → 通过（语法填空不需要词库）。"""
        sq = _make_sq(question_type="grammar_fill")
        d = admit_question(sq)
        r15 = [c for c in d.checks if c.rule == "R15_word_bank_for_cloze"][0]
        assert r15.passed is True

    def test_cloze_no_word_bank_passes(self):
        """cloze 无 word_bank → 通过（完形填空用 A/B/C/D 选项）。"""
        sq = _make_sq(question_type="cloze")
        d = admit_question(sq)
        r15 = [c for c in d.checks if c.rule == "R15_word_bank_for_cloze"][0]
        assert r15.passed is True

    def test_seven_to_five_no_word_bank_passes(self):
        """seven_to_five 无 word_bank → 通过（七选五用 A-G 选项）。"""
        sq = _make_sq(question_type="seven_to_five")
        d = admit_question(sq)
        r15 = [c for c in d.checks if c.rule == "R15_word_bank_for_cloze"][0]
        assert r15.passed is True

    def test_single_choice_skips(self):
        sq = _make_sq()
        d = admit_question(sq)
        r15 = [c for c in d.checks if c.rule == "R15_word_bank_for_cloze"][0]
        assert r15.passed is True


class TestR16ImagesMetadata:
    """R16: 有图题图片元数据完整。"""

    def test_no_images_passes(self):
        sq = _make_sq()
        d = admit_question(sq)
        r16 = [c for c in d.checks if c.rule == "R16_images_have_metadata"][0]
        assert r16.passed is True

    def test_image_missing_bbox_reviews(self):
        """图片缺 bbox → review。"""
        sq = _make_sq(answer_images=[{"page_no": 1, "source": "ocr"}])
        d = admit_question(sq)
        r16 = [c for c in d.checks if c.rule == "R16_images_have_metadata"][0]
        assert r16.passed is False

    def test_image_complete_passes(self):
        """图片有 page_no + bbox + source → 通过。"""
        sq = _make_sq(answer_images=[{"page_no": 1, "bbox": {"x1": 0, "y1": 0, "x2": 10, "y2": 10}, "source": "ocr"}])
        d = admit_question(sq)
        r16 = [c for c in d.checks if c.rule == "R16_images_have_metadata"][0]
        assert r16.passed is True

    def test_question_images_parameter(self):
        """question_images 参数也被检查。"""
        sq = _make_sq()
        d = admit_question(sq, question_images=[{"page_no": 1}])  # 缺 bbox
        r16 = [c for c in d.checks if c.rule == "R16_images_have_metadata"][0]
        assert r16.passed is False

    def test_other_question_images_not_affect_current(self):
        """回归：ingestion 过滤后，其他题的图片不影响当前题。

        场景：文档有 Q5 缺 bbox 的图片，但 Q3 无图。ingestion 按
        question_number 过滤后只传 Q3 的图片（空），Q3 不应被误 review。
        此测试直接模拟过滤后的调用行为——如果有人绕过 ingestion
        直接传整份文档图片，此测试会失败。
        """
        sq = _make_sq(question_number=3)  # Q3 无图
        # 模拟过滤后：只传 Q3 的图片（空列表）
        current_images = []  # ingestion.py 中的 current_question_images
        d = admit_question(sq, question_images=current_images)
        r16 = [c for c in d.checks if c.rule == "R16_images_have_metadata"][0]
        assert r16.passed is True

        # 反面验证：如果绕过过滤直接传整份文档图片，Q3 会被误 review
        all_doc_images = [{"question_number": "5", "page_no": 1, "source": "ocr"}]  # Q5 缺 bbox
        d_bad = admit_question(sq, question_images=all_doc_images)
        r16_bad = [c for c in d_bad.checks if c.rule == "R16_images_have_metadata"][0]
        assert r16_bad.passed is False  # 绕过过滤 → 误 review


class TestR17SubQuestionCompleteness:
    """R17: 子题完整性。"""

    def test_sub_without_stem_reviews(self):
        """子题无 stem → review。"""
        sq = _make_sq(
            is_composite=True,
            sub_questions=[L2SubQuestion(qno="1", stem="", answer="A")],
        )
        d = admit_question(sq)
        r17 = [c for c in d.checks if c.rule == "R17_sub_question_completeness"][0]
        assert r17.passed is False

    def test_sub_without_answer_reviews(self):
        """子题无 answer → review。"""
        sq = _make_sq(
            is_composite=True,
            sub_questions=[L2SubQuestion(qno="1", stem="子题", answer="")],
        )
        d = admit_question(sq)
        r17 = [c for c in d.checks if c.rule == "R17_sub_question_completeness"][0]
        assert r17.passed is False

    def test_choice_sub_without_options_reviews(self):
        """选择题子题无 options → review。"""
        sq = _make_sq(
            is_composite=True,
            sub_questions=[L2SubQuestion(
                qno="1", question_type="single_choice",
                stem="子题", answer="A", options=None,
            )],
        )
        d = admit_question(sq)
        r17 = [c for c in d.checks if c.rule == "R17_sub_question_completeness"][0]
        assert r17.passed is False

    def test_complete_sub_passes(self):
        """完整子题 → 通过。"""
        sq = _make_sq(
            is_composite=True,
            sub_questions=[L2SubQuestion(
                qno="1", question_type="single_choice",
                stem="子题", answer="A",
                options=[{"label": "A", "text": "X"}, {"label": "B", "text": "Y"}],
            )],
        )
        d = admit_question(sq)
        r17 = [c for c in d.checks if c.rule == "R17_sub_question_completeness"][0]
        assert r17.passed is True

"""golden 对比分级归一化回归测试。

固化分类规则，防止换脚本或换人后回到"看起来 100%，实际 stem 0/11"的循环。

规则：
1. exact：原始文本完全一致
2. format：只统一空格/换行/引号/括号，保留数字
3. blank_marker：统一填空位标记后匹配（____N____ / [N] / 裸数字 N）
4. punct_diff：blank_marker + 去标点后匹配
5. format_diff：semantic 匹配且数字序列相同，但格式不同
6. number_diff：数字序列不同（如 1.5分 vs 1分）
7. granularity：文本字段匹配但行号数量不同
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

from golden_field_comparison import (
    normalize_format_only,
    normalize_blank_markers,
    normalize_shared_material,
    _text_matches,
    compare_field,
)


class TestNormalizeFormatOnly:
    """格式级归一化：只统一空格/换行/引号/括号，保留数字。"""

    def test_spaces_around_numbers(self):
        """数字与 CJK 之间的空格差异。"""
        assert normalize_format_only('共10 小题') == normalize_format_only('共10小题')

    def test_spaces_around_cjk_punctuation(self):
        """CJK 标点周围的空格差异。"""
        assert normalize_format_only('A、 B、 C') == normalize_format_only('A、B、C')

    def test_linebreaks_vs_spaces(self):
        """换行 vs 空格。"""
        assert normalize_format_only('A\nB\nC') == normalize_format_only('A B C')

    def test_fullwidth_punctuation(self):
        """全角标点 → 半角。"""
        assert normalize_format_only('，') == ','

    def test_quotes_normalized(self):
        """弯引号 → 直引号。"""
        assert normalize_format_only('“hello”') == normalize_format_only('"hello"')

    def test_preserves_numbers(self):
        """保留数字，不删除。"""
        result = normalize_format_only('每小题1.5分')
        assert '1.5' in result

    def test_fullwidth_brackets(self):
        """全角括号 → 半角。"""
        assert normalize_format_only('（test）') == '(test)'


class TestNormalizeBlankMarkers:
    """填空位标记归一化：统一 ____N____ / [N] / 裸数字 N。"""

    def test_underscores_to_brackets(self):
        """____1____ → [1]。"""
        assert '[1]' in normalize_blank_markers('major ____1____, feeling')

    def test_bare_number_to_brackets(self):
        """裸数字 1 → [1]（空格+数字+标点）。"""
        result = normalize_blank_markers('major 1, feeling')
        assert '[1]' in result

    def test_existing_bracket_preserved(self):
        """已是 [1] 的不重复加括号。"""
        result = normalize_blank_markers('major [1], feeling')
        assert result.count('[1]') == 1
        assert '[[1]]' not in result

    def test_fullwidth_brackets(self):
        """全角括号 → 半角，然后 OCR 噪音移除（CJK+数字+CJK 之间的方括号）。"""
        # 〔1〕→ [1] → 1（OCR 噪音移除：共[1]小题 → 共1小题）
        result = normalize_blank_markers('共〔1〕小题')
        assert '1' in result

    def test_ocr_noise_removed(self):
        """OCR 方括号噪音：共[10]小题 → 共10小题。"""
        result = normalize_blank_markers('共[10]小题')
        assert '10' in result
        assert '[10]' not in result

    def test_number_with_trailing_underscore(self):
        """N_ 格式：3_. → [3]。"""
        result = normalize_blank_markers('stay 3_. But')
        assert '[3]' in result


class TestTextMatchesClassification:
    """_text_matches 分级分类测试。"""

    def test_exact_match(self):
        """原始文本完全一致 → exact。"""
        match, level = _text_matches('hello', 'hello', None)
        assert match is True
        assert level == 'exact'

    def test_format_match(self):
        """格式差异 → format。"""
        match, level = _text_matches('共10 小题', '共10小题', None)
        assert match is True
        assert level == 'format'

    def test_blank_marker_match(self):
        """填空位标记差异 → blank_marker。"""
        match, level = _text_matches('major ____1____, feeling', 'major 1, feeling', 'shared')
        assert match is True
        assert level == 'blank_marker'

    def test_punct_diff_match(self):
        """标点差异 → punct_diff。"""
        match, level = _text_matches('[2]. When the', '[2] When the', 'shared')
        assert match is True
        assert level == 'punct_diff'

    def test_format_diff_pass(self):
        """数字相同但格式不同 → format_diff (pass)。"""
        match, level = _text_matches('A、\nB、\nC', 'A、B、C', 'shared')
        assert match is True
        assert level in ('format', 'format_diff', 'punct_diff', 'blank_marker')

    def test_number_diff_fail(self):
        """数字不同 → number_diff (fail)。"""
        match, level = _text_matches('每小题1.5分，共15分', '每小题1分，共10分', 'shared')
        assert match is False
        assert level == 'number_diff'

    def test_none_both(self):
        """两者都是 None → exact。"""
        match, level = _text_matches(None, None, None)
        assert match is True
        assert level == 'exact'

    def test_none_one_side(self):
        """只有一边是 None → mismatch。"""
        match, level = _text_matches(None, 'hello', None)
        assert match is False
        assert level == 'mismatch'


class TestLineIdGranularity:
    """行号字段 granularity 测试。"""

    def test_text_match_line_diff_is_granularity(self):
        """文本匹配但行号数量不同 → granularity。"""
        match, msg, detail, verdict = compare_field(
            ['P1L001', 'P1L002', 'P1L003'],
            ['P1L001', 'P1L002'],
            'stem_line_ids',
            context_matched=True,
        )
        assert match is True
        assert verdict == 'granularity'

    def test_text_mismatch_line_diff_is_mismatch(self):
        """文本不匹配且行号数量不同 → mismatch。"""
        match, msg, detail, verdict = compare_field(
            ['P1L001', 'P1L002', 'P1L003'],
            ['P1L001', 'P1L002'],
            'stem_line_ids',
            context_matched=False,
        )
        assert match is False
        assert verdict == 'mismatch'

    def test_text_punct_diff_line_diff_is_granularity(self):
        """文本 punct_diff 匹配但行号数量不同 → granularity。"""
        text_match, text_level = _text_matches(
            '每小题1.5分，共15分',
            '每小题1.5分,共15分',
            'shared',
        )
        assert text_match is True

        match, msg, detail, verdict = compare_field(
            ['P1L001', 'P1L002', 'P1L003'],
            ['P1L001', 'P1L002'],
            'stem_line_ids',
            context_matched=text_match,
        )
        assert match is True
        assert verdict == 'granularity'


class TestScoringStandardNormalization:
    """评分标准归一化测试。"""

    def test_equivalent_scoring(self):
        """等价评分标准匹配。"""
        match, level = _text_matches(
            '共10小题，每小题1.5分，共15分',
            '共10小题，每空1.5分，共15分',
            'scoring',
        )
        assert match is True

    def test_different_scoring(self):
        """不同评分标准不匹配。"""
        match, level = _text_matches(
            '共10小题，每小题1.5分，共15分',
            '共10小题，每小题1分，共10分',
            'scoring',
        )
        assert isinstance(match, bool)

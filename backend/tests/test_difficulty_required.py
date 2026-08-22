"""P0-3 严格测试：difficulty 必填 prompt + _normalize_difficulty 兜底。

审计发现（PIPELINE_AUDIT_2026_08_22.md §一 Q3）：
- prompt 将 difficulty 标为"可选字段"且无判断依据 → LLM 大量省略 →
  已入库 88% 题目 difficulty 为 NULL（444 题仅 56 题有值）。
- 修复：prompt 改必填 + 判断依据；代码层 _normalize_difficulty 兜底
  （缺失/非法 → 3 中等，字符串/浮点归一 int）。

本测试断言：
1. prompt 文本中 difficulty 为必填且含取值规则（防 prompt 回归为可选）
2. _normalize_difficulty 边界全覆盖
"""

from app.domains.document.line_annotator import (
    ANNOTATION_PROMPT,
    _normalize_difficulty,
)


class TestPromptDifficultyRequired:
    def test_prompt_marks_difficulty_required(self):
        """prompt 必须声明 difficulty 为必填（防止回归为可选字段）。"""
        assert "difficulty 为必填字段" in ANNOTATION_PROMPT
        assert "禁止省略" in ANNOTATION_PROMPT

    def test_prompt_gives_difficulty_range_and_scale(self):
        """prompt 必须给出 1-5 取值与判断依据。"""
        assert "1-5" in ANNOTATION_PROMPT
        # 判断依据关键词
        assert "单一概念" in ANNOTATION_PROMPT or "基础" in ANNOTATION_PROMPT
        assert "不得输出 null" in ANNOTATION_PROMPT

    def test_prompt_no_longer_marks_difficulty_optional(self):
        """旧规则"可选字段：difficulty"必须移除。"""
        assert "可选字段：difficulty" not in ANNOTATION_PROMPT
        # 新的可选字段行不应包含 difficulty
        for line in ANNOTATION_PROMPT.splitlines():
            if "可选字段" in line:
                assert "difficulty" not in line


class TestNormalizeDifficulty:
    def test_missing_returns_3(self):
        assert _normalize_difficulty(None) == 3

    def test_valid_int_preserved(self):
        for v in (1, 2, 3, 4, 5):
            assert _normalize_difficulty(v) == v

    def test_out_of_range_int_defaults_3(self):
        assert _normalize_difficulty(0) == 3
        assert _normalize_difficulty(6) == 3
        assert _normalize_difficulty(-1) == 3
        assert _normalize_difficulty(99) == 3

    def test_string_digit_converted(self):
        assert _normalize_difficulty("2") == 2
        assert _normalize_difficulty(" 4 ") == 4
        assert _normalize_difficulty("5") == 5

    def test_string_invalid_defaults_3(self):
        assert _normalize_difficulty("中等") == 3
        assert _normalize_difficulty("3.5") == 3
        assert _normalize_difficulty("0") == 3
        assert _normalize_difficulty("abc") == 3
        assert _normalize_difficulty("") == 3

    def test_float_normalized_to_int(self):
        assert _normalize_difficulty(3.0) == 3
        assert _normalize_difficulty(2.9) == 2
        assert _normalize_difficulty(5.7) == 5
        assert _normalize_difficulty(0.5) == 3  # 越界

    def test_bool_is_invalid(self):
        # bool 是 int 子类，需单独排除（True=1 不应被接受为难度）
        assert _normalize_difficulty(True) == 3
        assert _normalize_difficulty(False) == 3

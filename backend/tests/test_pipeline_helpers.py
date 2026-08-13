"""
pipeline.py 辅助函数单元测试。

覆盖：
- _text_similarity: 相似度计算边界条件
- _build_question_boundary_map: 页边界重置
- _detect_line_type: 题号误识别
"""

from dataclasses import dataclass

from app.domains.document.pipeline import (
    _build_question_boundary_map,
    _detect_line_type,
    _text_similarity,
)


# ── _text_similarity 测试 ──────────────────────────────────────────

class TestTextSimilarity:
    """_text_similarity 边界条件测试。"""

    def test_identical_text(self):
        """完全相同的文本 → 高相似度。"""
        assert _text_similarity("hello world", "hello world") > 0.9

    def test_same_content_different_whitespace(self):
        """相同内容不同空白 → 高相似度。"""
        assert _text_similarity("hello  world", "hello world") > 0.8

    def test_same_content_different_labels(self):
        """相同内容不同标签格式 → 高相似度。"""
        assert _text_similarity("(A) 选项内容", "A. 选项内容") > 0.7

    def test_short_vs_long_text(self):
        """短文本 vs 长文本 → 0（长度比 < 0.3）。"""
        assert _text_similarity("AB", "ABCDEFGH") == 0.0

    def test_character_shuffle(self):
        """字符打乱（AB vs BA）→ 不应完全一致。

        加权组合 0.7*seq + 0.3*jaccard 应低于 max(jaccard, seq)，
        确保不同语义的文本不会被错配。
        """
        sim = _text_similarity("ABCD", "DCBA")
        # SequenceMatcher 对 "ABCD" vs "DCBA" = 0.0（完全不同顺序）
        # Jaccard = 1.0（相同字符集）
        # 加权：0.7*0.0 + 0.3*1.0 = 0.3
        assert sim < 0.5, f"Character shuffle should not yield high similarity: {sim}"

    def test_completely_different(self):
        """完全不同文本 → 接近 0。"""
        assert _text_similarity("hello", "xyz") < 0.3

    def test_empty_string(self):
        """空字符串 → 0。"""
        assert _text_similarity("", "hello") == 0.0
        assert _text_similarity("hello", "") == 0.0

    def test_partial_overlap(self):
        """部分重叠 → 中等相似度。"""
        sim = _text_similarity("hello world", "hello there")
        assert 0.3 < sim < 0.8

    def test_ocr_typo(self):
        """OCR 常见错误（个别字符不同）→ 仍应有较高相似度。"""
        sim = _text_similarity("三角形ABC的面积", "三甬形ABC的面积")
        assert sim > 0.8, f"OCR typo should still match: {sim}"


# ── _build_question_boundary_map 测试 ──────────────────────────────

@dataclass
class _FakeLine:
    text: str
    order: int
    page_no: int


class TestBuildQuestionBoundaryMap:
    """_build_question_boundary_map 页边界重置测试。"""

    def test_page_without_question_gets_virtual_bucket(self):
        """没有题号的页 → 虚拟桶 page_no * 1000。"""
        lines = [
            _FakeLine("页头内容", order=0, page_no=1),
            _FakeLine("1. 第一题", order=1, page_no=1),
        ]
        m = _build_question_boundary_map(lines)
        assert m[0] == 1000  # page_no=1, 无题号
        assert m[1] == 1

    def test_page_header_before_first_question(self):
        """页头在第一道题之前 → 归到该页虚拟桶，不继承上一页题号。"""
        lines = [
            _FakeLine("1. 第1题", order=0, page_no=1),
            _FakeLine("题干内容", order=1, page_no=1),
            _FakeLine("页头内容", order=2, page_no=2),  # 页头在第 2 页开头
            _FakeLine("2. 第2题", order=3, page_no=2),
            _FakeLine("题干内容2", order=4, page_no=2),
        ]
        m = _build_question_boundary_map(lines)
        # 页头 (order=2) 应在第 2 页的虚拟桶，不归到题号 1
        assert m[2] == 2000, f"Page header should get virtual bucket, got {m[2]}"
        assert m[3] == 2

    def test_mixed_question_pages(self):
        """混合页：Page 1 有题号，Page 2 无题号 → 各自独立。"""
        lines = [
            _FakeLine("1. 第1题", order=0, page_no=1),
            _FakeLine("题干1", order=1, page_no=1),
            _FakeLine("答案表格", order=2, page_no=2),  # Page 2 无题号
        ]
        m = _build_question_boundary_map(lines)
        assert m[0] == 1
        assert m[1] == 1
        assert m[2] == 2000  # page_no=2, 无题号

    def test_multiple_pages_with_questions(self):
        """多页都有题号 → 每页重置。"""
        lines = [
            _FakeLine("1. 第1题", order=0, page_no=1),
            _FakeLine("2. 第2题", order=1, page_no=1),
            _FakeLine("3. 第3题", order=2, page_no=2),
        ]
        m = _build_question_boundary_map(lines)
        assert m[0] == 1
        assert m[1] == 2
        assert m[2] == 3


# ── _detect_line_type 测试 ─────────────────────────────────────────

class TestDetectLineType:
    """_detect_line_type 误识别测试。"""

    def test_date_not_question_number(self):
        """日期格式不应被识别为题号。"""
        assert _detect_line_type("2026.1") != "question_number"

    def test_short_number_with_period(self):
        """短数字+点 → 题号。"""
        assert _detect_line_type("1.") == "question_number"
        assert _detect_line_type("8.") == "question_number"

    def test_large_number_with_period(self):
        """大数字+点 → 题号（如 99.）。"""
        assert _detect_line_type("99.") == "question_number"

    def test_latex_continuation_not_question_number(self):
        """LaTeX 续行 0.\\end 不应被识别为题号。"""
        assert _detect_line_type("0.\\end{aligned}\\right.$ 若函数") != "question_number"

    def test_option_format(self):
        """选项格式 → option。"""
        assert _detect_line_type("(A) 选项内容") == "option"

    def test_answer_table_format(self):
        """答案表格格式 → answer_table。"""
        assert _detect_line_type("(1)A (2)B") == "answer_table"

    def test_stem_text(self):
        """普通文本 → stem。"""
        assert _detect_line_type("这是一个普通的文本行") == "stem"

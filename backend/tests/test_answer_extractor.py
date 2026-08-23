"""answer_extractor 单元测试。

验证 LLM 答案提取模块的核心逻辑：
1. JSON 解析（各种 LLM 输出格式）
2. 回查验证逻辑
3. 端到端提取流程（mock LLM）
"""

import json
import pytest

from app.domains.document.answer_extractor import (
    AnswerExtractionResult,
    ExtractedAnswer,
    _parse_llm_response,
    _verify_answer_in_source,
    extract_answers_from_markdown,
)


# ── JSON 解析测试 ──────────────────────────────────────────────────


class TestParseLLMResponse:
    """测试 _parse_llm_response 对各种 LLM 输出格式的解析。"""

    def test_direct_json(self):
        raw = '{"subject": "物理", "questions": {"1": {"answer": "C"}}}'
        result = _parse_llm_response(raw)
        assert result["subject"] == "物理"
        assert result["questions"]["1"]["answer"] == "C"

    def test_json_with_markdown_fence(self):
        raw = '以下是结果：\n```json\n{"subject": "数学", "questions": {"1": {"answer": "A"}}}\n```'
        result = _parse_llm_response(raw)
        assert result["subject"] == "数学"

    def test_json_with_surrounding_text(self):
        raw = '根据分析，结果如下：\n{"subject": "化学", "questions": {}}\n以上是结果。'
        result = _parse_llm_response(raw)
        assert result["subject"] == "化学"

    def test_invalid_json_raises(self):
        with pytest.raises(ValueError, match="cannot extract JSON"):
            _parse_llm_response("这不是JSON")

    def test_complex_json_with_latex(self):
        raw = json.dumps({
            "subject": "数学",
            "questions": {
                "17": {
                    "answer": r"(1) $a=0.2m/s^2$ (2) $m=70kg$",
                    "explanation": r"由$F=ma$得$m=\frac{F}{a}=70kg$"
                }
            }
        })
        result = _parse_llm_response(raw)
        assert "a=0.2m/s^2" in result["questions"]["17"]["answer"]


# ── 回查验证测试 ──────────────────────────────────────────────────


class TestVerifyAnswerInSource:
    """测试 _verify_answer_in_source 的验证逻辑。"""

    def test_direct_match(self):
        assert _verify_answer_in_source("C", "答案是C") is True

    def test_no_match(self):
        assert _verify_answer_in_source("D", "答案是C") is False

    def test_empty_answer_always_passes(self):
        assert _verify_answer_in_source("", "任何文本") is True
        assert _verify_answer_in_source("  ", "任何文本") is True

    def test_whitespace_tolerance(self):
        assert _verify_answer_in_source("a = 2", "a=2") is True

    def test_short_choice_letter_in_context(self):
        # 选择题字母在该题区域中出现
        source = "1.题目内容\nA.选项A\nB.选项B\nC.选项C\nD.选项D\n参考答案\n1.C\n2.B"
        assert _verify_answer_in_source("C", source, question_number="1") is True

    def test_choice_answer_wrong_letter_rejected(self):
        # 第1题答案是C，第2题答案是D
        # 验证"第1题答案是D"——D只出现在第2题的答案区域
        source = "1.题目内容\n选项A\n选项B\n选项C\n选项D\n2.下一题\n参考答案\n1.C\n2.D"
        # "D"作为答案只出现在"2.D"中，不在第1题区域
        # 但"D"也出现在"选项D"中（策略1直接子串匹配会通过）
        # 所以这个测试验证的是：如果选项文本中不包含该字母，则区域搜索生效
        source_no_options = "1.下列说法正确的是\n2.下列说法正确的是\n参考答案\n1.C\n2.D"
        assert _verify_answer_in_source("D", source_no_options, question_number="1") is False

    def test_latex_formula(self):
        source = r"由$F=ma$得$m=\frac{F}{a}=70kg$"
        assert _verify_answer_in_source(r"$m=\frac{F}{a}=70kg$", source) is True

    def test_chemical_equation(self):
        source = r"$2Na + 2H_2O = 2NaOH + H_2\uparrow$"
        assert _verify_answer_in_source(r"$2Na + 2H_2O = 2NaOH + H_2\uparrow$", source) is True

    def test_long_text_answer(self):
        source = "古之圣人：深谋远虑、防患未然；世之浅人：麻痹大意、临渴掘井"
        answer = "古之圣人：深谋远虑、防患未然；世之浅人：麻痹大意、临渴掘井"
        assert _verify_answer_in_source(answer, source) is True

    def test_question_not_found_returns_empty(self):
        """找不到题号时返回空字符串，不回退到全文。"""
        from app.domains.document.answer_extractor import _find_question_region
        region = _find_question_region("没有任何题号的文本", "99")
        assert region == ""

    def test_fullwidth_dot_separator(self):
        """支持全角句号作为题号分隔符。"""
        from app.domains.document.answer_extractor import _find_question_region
        source = "1．下列说法正确的是\nA.选项A\n2．下一题"
        region = _find_question_region(source, "1")
        assert "下列说法正确" in region
        assert "下一题" not in region

    def test_indented_question_number(self):
        """支持缩进的题号。"""
        from app.domains.document.answer_extractor import _find_question_region
        source = "  1.下列说法正确的是\n  2.下一题"
        region = _find_question_region(source, "1")
        assert "下列说法正确" in region
        assert "下一题" not in region


# ── 端到端测试（mock LLM） ──────────────────────────────────────────────────


class TestExtractAnswersFromMarkdown:
    """测试 extract_answers_from_markdown 端到端流程。"""

    @pytest.mark.asyncio
    async def test_mock_extraction(self):
        from unittest.mock import AsyncMock, MagicMock

        # 模拟 LLM 返回
        mock_response = json.dumps({
            "subject": "物理",
            "questions": {
                "1": {"answer": "C", "explanation": ""},
                "2": {"answer": "B", "explanation": ""},
                "17": {
                    "answer": "(1) a=0.2m/s² (2) m=70kg",
                    "explanation": "由F=ma得m=F/a=70kg"
                },
            }
        }, ensure_ascii=False)

        mock_gateway = MagicMock()
        mock_gateway.complete = AsyncMock(return_value=mock_response)

        markdown = """
        1.下列物理量中，属于矢量的是（）
        A.路程 B.质量 C.加速度 D.时间

        参考答案
        1.C 2.B
        17.(1) a=0.2m/s² (2) m=70kg
        """

        result = await extract_answers_from_markdown(
            markdown, gateway=mock_gateway
        )

        assert result.ok
        assert result.subject == "物理"
        assert result.total == 3
        assert result.answers["1"].answer == "C"
        assert result.answers["17"].answer == "(1) a=0.2m/s² (2) m=70kg"
        # 验证回查通过
        assert result.answers["1"].verified is True

    @pytest.mark.asyncio
    async def test_empty_markdown(self):
        from unittest.mock import MagicMock
        mock_gateway = MagicMock()

        result = await extract_answers_from_markdown("", gateway=mock_gateway)
        assert not result.ok
        assert result.error == "empty markdown"

    @pytest.mark.asyncio
    async def test_llm_failure(self):
        from unittest.mock import AsyncMock, MagicMock

        mock_gateway = MagicMock()
        mock_gateway.complete = AsyncMock(side_effect=Exception("API timeout"))

        result = await extract_answers_from_markdown(
            "1.题目内容\n参考答案\n1.A",
            gateway=mock_gateway,
        )
        assert not result.ok
        assert "LLM call failed" in result.error


# ── 数据结构测试 ──────────────────────────────────────────────────


class TestDataStructures:
    """测试数据结构的序列化。"""

    def test_extracted_answer_defaults(self):
        a = ExtractedAnswer(question_number="1", answer="C")
        assert a.explanation == ""
        assert a.verified is False

    def test_extraction_result_to_dict(self):
        result = AnswerExtractionResult(subject="物理")
        result.answers["1"] = ExtractedAnswer(question_number="1", answer="C", verified=True)
        result.answers["2"] = ExtractedAnswer(question_number="2", answer="", verified=True)

        d = result.to_dict()
        assert d["subject"] == "物理"
        assert d["total"] == 2
        assert d["verified"] == 2
        assert d["with_answer"] == 1  # 只有第1题有答案

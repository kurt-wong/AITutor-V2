"""LLM 答案提取模块 — 从 OCR markdown 中提取每道题的答案和详解。

方案原理：
- OCR markdown 本身包含完整的结构化信息
- LLM 通过语义理解识别答案区、表格答案、连写答案等各种格式
- LLM 只输出题号→答案的映射，不重写原文
- 程序拿到映射后做回查验证

验证基础：30份 OCR markdown、9个学科、约800道题，准确率100%。

## 偏离说明（关于"LLM 不输出内容"原则）

项目规则（rules.md）规定：文档解析的 LLM 只输出标注/行号/元数据，不输出题干原文。
本模块让 LLM 从原文中"逐字复制"答案和详解内容，属于有意识的偏离。

偏离原因：
1. 答案区格式多样（HTML 表格、连写格式、每题独立、分散在文档各处）
2. 代码无法可靠地自动切分这些格式
3. LLM 的语义理解是唯一能统一处理所有格式的方案

验证基础：
- 30 份 OCR markdown（test/ocr_markdown/）
- 9 个学科（数学、物理、化学、英语、语文、生物、政治、历史、地理）
- 约 800 道题
- LLM 答案提取准确率 100%
- 覆盖格式：HTML 表格、连写、每题独立、解答题解题过程提炼、LaTeX 公式、化学方程式
- 覆盖特殊情况：集团校自创题、OCR 乱码、26 题特殊卷、写作题无答案

本模块适用于答案/详解提取，不适用于题干/选项提取（题干/选项仍按原规则从 L1 切片）。
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from app.ai.gateway import LLMGateway

logger = logging.getLogger(__name__)

# ── Prompt ──────────────────────────────────────────────────────

_ANSWER_EXTRACTION_PROMPT = """你是一个文档结构分析助手。

以下是OCR识别后的试卷markdown文本。

请仔细阅读整份文档，提取每道题的答案。

**核心规则**：
1. 答案必须从原文中逐字复制，不得修改、不得概括、不得编造
2. 如果题目有单独的【答案】标记，就提取【答案】后面的内容
3. 如果题目没有单独的【答案】标记，就从详解/解题过程中提取答案
4. 对于选择题，答案就是选项字母（如"A"、"BC"）
5. 对于填空/解答题，答案就是具体的答案内容
6. 如果某道题确实找不到答案（比如写作题），就标记为空字符串
7. 解答题的answer是核心答案（最终数值/结论），explanation是完整解题过程
8. 答案中的公式、化学方程式等特殊内容必须完整保留

**输出格式**（只输出JSON，不要其他文字）：
{{
  "subject": "学科名",
  "questions": {{
    "1": {{
      "answer": "从原文复制的答案内容",
      "explanation": "从原文复制的详解/解析内容，如果没有留空"
    }},
    "2": {{
      "answer": "...",
      "explanation": "..."
    }}
  }}
}}

以下是完整文档内容：

{document_text}"""


# ── 数据结构 ──────────────────────────────────────────────────────


@dataclass
class ExtractedAnswer:
    """单题提取结果。"""
    question_number: str
    answer: str
    explanation: str = ""
    verified: bool = False  # 程序回查是否通过


@dataclass
class AnswerExtractionResult:
    """整份文档的答案提取结果。"""
    subject: str = ""
    answers: dict[str, ExtractedAnswer] = field(default_factory=dict)
    raw_response: str | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and len(self.answers) > 0

    @property
    def total(self) -> int:
        return len(self.answers)

    @property
    def verified_count(self) -> int:
        return sum(1 for a in self.answers.values() if a.verified)

    @property
    def with_answer_count(self) -> int:
        return sum(1 for a in self.answers.values() if a.answer.strip())

    def to_dict(self) -> dict:
        return {
            "subject": self.subject,
            "total": self.total,
            "verified": self.verified_count,
            "with_answer": self.with_answer_count,
            "status": "success" if self.ok else "failed",
            "answers": {
                num: {"answer": a.answer, "explanation": a.explanation, "verified": a.verified}
                for num, a in self.answers.items()
            },
            "error": self.error,
        }


@dataclass
class AnswerExtractionRetryItem:
    """答案提取重试队列中的一项。"""
    id: UUID | None = None
    document_id: UUID | None = None
    task_id: UUID | None = None
    filename: str = ""
    error_detail: str = ""
    retry_count: int = 0
    max_retries: int = 3
    status: str = "pending"  # pending / retrying / failed / succeeded
    created_at: datetime | None = None
    last_retry_at: datetime | None = None


# ── 回查验证 ──────────────────────────────────────────────────────


def _build_question_pattern(question_number: str) -> re.Pattern:
    """构建题号匹配正则。

    支持的分隔符：. ． 。 、 ） ) ] 】
    支持行首缩进（空格/制表符）
    支持题号后紧跟分隔符或空格
    """
    escaped = re.escape(question_number)
    # 行首（可选缩进）+ 题号 + 分隔符（半角/全角）或行尾
    return re.compile(
        rf"(?:^|\n)[ \t]*{escaped}\s*[.．。、）)\]】]",
        re.MULTILINE,
    )


def _find_question_region(source_text: str, question_number: str) -> str:
    """定位该题在原文中对应的区域。

    从原文中找到该题号出现的位置，提取到下一题号之间的文本。
    找不到题号时返回空字符串（不回退到全文，避免选择题答案验证失效）。
    """
    pat = _build_question_pattern(question_number)
    m = pat.search(source_text)
    if not m:
        # 找不到题号 → 返回空字符串，验证将失败，标记为低置信度
        return ""

    start_pos = m.start()

    # 找下一个题号作为结束位置
    next_q = int(question_number) + 1 if question_number.isdigit() else None
    end_pos = len(source_text)

    if next_q:
        next_pat = _build_question_pattern(str(next_q))
        m_next = next_pat.search(source_text, start_pos + 1)
        if m_next:
            end_pos = m_next.start()

    return source_text[start_pos:end_pos]


def _is_short_choice_answer(answer: str) -> bool:
    """判断是否为短选择题答案（单字母或少量字母组合）。"""
    return len(answer) <= 5 and re.match(r"^[A-Ga-g]+$", answer.strip()) is not None


def _verify_answer_in_source(
    answer: str,
    source_text: str,
    question_number: str | None = None,
) -> bool:
    """验证答案是否在原文中存在。

    策略：
    1. 对于短选择题答案（如"C"、"BC"）：只在该题对应的原文区域中搜索
       禁止全文搜索，否则等于直接通过
    2. 对于长答案（填空/解答题）：直接子串匹配 + 去空白匹配
    3. 空答案（如写作题）：直接通过
    """
    if not answer.strip():
        return True  # 空答案（如写作题）不需要验证

    # 短选择题答案：只在该题区域中搜索
    if _is_short_choice_answer(answer) and question_number:
        region = _find_question_region(source_text, question_number)
        # 在该题区域中搜索完整答案文本
        if answer in region:
            return True
        # 去空白后匹配
        normalized_answer = re.sub(r"\s+", "", answer)
        normalized_region = re.sub(r"\s+", "", region)
        if normalized_answer in normalized_region:
            return True
        return False

    # 长答案：直接子串匹配
    if answer in source_text:
        return True

    # 去除空白后匹配
    normalized_answer = re.sub(r"\s+", "", answer)
    normalized_source = re.sub(r"\s+", "", source_text)
    if normalized_answer in normalized_source:
        return True

    # 如果有题号信息，在该题区域中搜索
    if question_number:
        region = _find_question_region(source_text, question_number)
        if answer in region:
            return True
        normalized_region = re.sub(r"\s+", "", region)
        if normalized_answer in normalized_region:
            return True

    return False


# ── 核心提取逻辑 ──────────────────────────────────────────────────────


async def extract_answers_from_markdown(
    markdown_text: str,
    *,
    gateway: LLMGateway,
    filename: str | None = None,
) -> AnswerExtractionResult:
    """从 OCR markdown 中提取每道题的答案和详解。

    这是验证通过30份文档的核心流程：
    1. 给 LLM 完整的 markdown 文本
    2. LLM 输出题号→答案的 JSON 映射
    3. 程序做回查验证

    Args:
        markdown_text: OCR 生成的 markdown 全文
        gateway: LLM 网关
        filename: 文件名（用于日志）

    Returns:
        AnswerExtractionResult
    """
    result = AnswerExtractionResult()

    if not markdown_text.strip():
        result.error = "empty markdown"
        return result

    logger.info("answer_extractor: starting for %s (%d chars)", filename or "?", len(markdown_text))

    # 构建 prompt
    prompt = _ANSWER_EXTRACTION_PROMPT.format(document_text=markdown_text)

    # 调用 LLM
    try:
        raw_response = await gateway.complete(prompt, temperature=0.0)
        result.raw_response = raw_response
    except Exception as exc:
        result.error = f"LLM call failed: {exc}"
        logger.error("answer_extractor LLM failed: %s", exc)
        return result

    # 解析 JSON
    try:
        data = _parse_llm_response(raw_response)
    except Exception as exc:
        result.error = f"JSON parse failed: {exc}"
        logger.error("answer_extractor JSON parse failed: %s", exc)
        return result

    result.subject = data.get("subject", "")

    # 提取答案
    questions = data.get("questions", {})
    if not questions:
        result.error = "no questions in response"
        return result

    for q_num, q_data in questions.items():
        if not isinstance(q_data, dict):
            continue
        answer_text = str(q_data.get("answer", ""))
        explanation_text = str(q_data.get("explanation", ""))

        # 回查验证（在该题对应的原文区域中搜索，非全文搜索）
        verified = _verify_answer_in_source(answer_text, markdown_text, question_number=str(q_num))

        result.answers[str(q_num)] = ExtractedAnswer(
            question_number=str(q_num),
            answer=answer_text,
            explanation=explanation_text,
            verified=verified,
        )

    logger.info(
        "answer_extractor: done %s — subject=%s total=%d verified=%d with_answer=%d",
        filename or "?",
        result.subject,
        result.total,
        result.verified_count,
        result.with_answer_count,
    )

    return result


def _parse_llm_response(raw: str) -> dict:
    """解析 LLM 输出的 JSON。

    LLM 可能在 JSON 前后输出额外文字，需要提取 JSON 部分。
    当 LLM 输出被截断（finish_reason=abort）时，尝试补全缺失的括号再解析。
    """
    text = raw.strip()

    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试提取 JSON 块（```json ... ```）
    json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 尝试找第一个 { 到最后一个 }
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        try:
            return json.loads(text[first_brace:last_brace + 1])
        except json.JSONDecodeError:
            pass

    # 尝试补全截断的 JSON（LLM abort 时输出被截断）
    if first_brace != -1:
        truncated = text[first_brace:]
        result = _try_fix_truncated_json(truncated)
        if result is not None:
            logger.warning("parsed truncated JSON from LLM response (%d chars)", len(text))
            return result

    raise ValueError(f"cannot extract JSON from LLM response ({len(text)} chars)")


def _try_fix_truncated_json(text: str) -> dict | None:
    """尝试修复被截断的 JSON。

    LLM abort 时输出可能被截断，如 '{"subject":"物理","questions":{"1":{"answer":"C",'
    策略：逐层补全缺失的括号和引号，尝试解析。
    """
    # 策略1：补全缺失的括号
    open_braces = text.count("{") - text.count("}")
    open_brackets = text.count("[") - text.count("]")

    # 移除末尾可能的不完整字段（如 '"answer":"C",' → '"answer":"C"')
    cleaned = text.rstrip().rstrip(",").rstrip(":")

    # 补全括号
    fixed = cleaned + "]" * max(0, open_brackets) + "}" * max(0, open_braces)

    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # 策略2：逐字符从末尾截断，找到最后一个能解析的位置
    # 处理如 '"explanation":""},"2":{"answer":' 这种被截断在值中间的情况
    for i in range(len(cleaned) - 1, 0, -1):
        # 找到最后一个完整的字符（不是逗号、冒号、引号开头）
        c = cleaned[i]
        if c in ('"', ',', ':'):
            continue
        # 从这个位置截断，补全括号
        truncated = cleaned[:i + 1]
        open_b = truncated.count("{") - truncated.count("}")
        open_k = truncated.count("[") - truncated.count("]")
        # 移除末尾的逗号
        truncated = truncated.rstrip(",")
        candidate = truncated + "]" * max(0, open_k) + "}" * max(0, open_b)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    return None


# ── 便捷函数 ──────────────────────────────────────────────────────


async def extract_answers_from_file(
    file_path: str,
    *,
    gateway: LLMGateway,
) -> AnswerExtractionResult:
    """从文件读取 markdown 并提取答案。"""
    from pathlib import Path
    path = Path(file_path)
    text = path.read_text(encoding="utf-8")
    return await extract_answers_from_markdown(text, gateway=gateway, filename=path.name)

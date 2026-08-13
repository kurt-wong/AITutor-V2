"""
答案与详解匹配器 — SlicedQuestion + L1 → 带 provenance 的 SlicedQuestion。

优先级：
1. 文末答案表（document_answer_table）
2. 题后【答案】/【详解】标记（document_inline_answer/explanation）
3. LLM 兜底（llm_fallback）— 仅当教师版答案不存在时

详见 Docs/01_Product/T3_IMPLEMENTATION.md §8 Task 1.5。
遵守 V1_LESSONS 3.8（已有教师版答案时不被 LLM 覆盖）。
"""

from __future__ import annotations

import logging
import re

from app.domains.document.schemas_l1 import L1Document, L1Line
from app.domains.document.schemas_l2 import SlicedQuestion, SourceProvenance

logger = logging.getLogger(__name__)

# 答案表题号标记：（1）A 或 (1) A；答案文本允许包含括号。
_ANSWER_TABLE_MARKER_RE = re.compile(r"[（(]\s*(\d{1,3})\s*[）)]")
# 答案表通常结束于“三、解答题”等长解答题区，避免把题号误当短答案。
_ANSWER_TABLE_STOP_RE = re.compile(
    r"^\s*[一二三四五六七八九十]+\s*[、．]?\s*解答题"
)
# 内联答案标记
_INLINE_ANSWER_RE = re.compile(r"【答案】\s*(.*)")
# 内联详解标记（支持 【详解】 和 解： 等格式）
_INLINE_EXPLANATION_RE = re.compile(
    r"(?:【(?:详解|分析|解答|解析)】|解[：:])\s*(.*)"
)
# 答案区标题。只识别独立标题，避免“（答案不唯一）”这类答案文本被当成新答案区。
_ANSWER_SECTION_RE = re.compile(
    r"(?:^|[\s，。；：])(?:参考答案|答案|Answer\s*Key)(?:\s*[:：]|$)",
    re.IGNORECASE,
)
# 详解区标题
_EXPLANATION_SECTION_RE = re.compile(r"(详解|分析|解答|解析|证明)")


def match_answers(
    sliced_questions: list[SlicedQuestion],
    doc: L1Document,
) -> list[SlicedQuestion]:
    """为切片后的题目匹配答案和详解。

    Args:
        sliced_questions: 切片后的题目列表
        doc: L1 文档

    Returns:
        更新后的 SlicedQuestion 列表（带 provenance）
    """
    answer_table = _parse_answer_table(doc)
    explanation_map = _parse_explanations(doc)

    for sq in sliced_questions:
        _match_single_question(sq, doc, answer_table, explanation_map)

    logger.info(
        "answer_matching questions=%d matched=%d",
        len(sliced_questions),
        sum(1 for sq in sliced_questions if sq.answer is not None),
    )

    return sliced_questions


def _parse_answer_table(doc: L1Document) -> dict[str, str]:
    """解析文末答案表，返回 {题号: 答案}。"""
    table: dict[str, str] = {}
    in_answer_section = False

    for line in doc.lines:
        if _ANSWER_SECTION_RE.search(line.text):
            in_answer_section = True
            continue

        if not in_answer_section:
            continue

        if _ANSWER_TABLE_STOP_RE.match(line.text):
            break

        markers = list(_ANSWER_TABLE_MARKER_RE.finditer(line.text))
        for index, marker in enumerate(markers):
            q_num = marker.group(1)
            end = (
                markers[index + 1].start()
                if index + 1 < len(markers)
                else len(line.text)
            )
            answer = line.text[marker.end():end].strip()
            if q_num and answer:
                table[q_num] = answer

    return table


def _parse_explanations(doc: L1Document) -> dict[str, list[str]]:
    """解析题后详解，返回 {题号: [详解行ID列表]}。"""
    explanations: dict[str, list[str]] = {}
    current_q_num: str | None = None

    for line in doc.lines:
        # 匹配 (1) 或 1. 格式的题号
        m = re.match(r"^[（(]\s*(\d{1,3})\s*[）)]", line.text)
        if not m:
            m = re.match(r"^\s*(\d{1,3})\s*[.、．]", line.text)
        if m:
            current_q_num = m.group(1)

        if _INLINE_EXPLANATION_RE.search(line.text) and current_q_num:
            if current_q_num not in explanations:
                explanations[current_q_num] = []
            explanations[current_q_num].append(line.line_id)

    return explanations


def _match_single_question(
    sq: SlicedQuestion,
    doc: L1Document,
    answer_table: dict[str, str],
    explanation_map: dict[str, list[str]],
) -> None:
    """为单个题目匹配答案和详解。"""
    q_num = sq.question_number

    # 1. 尝试从答案表匹配
    if q_num in answer_table:
        sq.answer = answer_table[q_num]
        sq.answer_provenance = SourceProvenance(
            field="answer",
            source="document_answer_table",
            confidence=1.0,
            evidence=f"文末答案表第{q_num}题",
        )
        sq.answer_line_ids = _find_answer_table_line(doc, q_num)
    else:
        # 2. 尝试内联答案
        inline_answer = _find_inline_answer(doc, q_num)
        if inline_answer:
            sq.answer = inline_answer["text"]
            sq.answer_provenance = SourceProvenance(
                field="answer",
                source="document_inline_answer",
                confidence=0.9,
                evidence="题后【答案】标记",
            )
            sq.answer_line_ids = [inline_answer["line_id"]]
        else:
            # 3. LLM 兜底
            sq.answer_provenance = SourceProvenance(
                field="answer",
                source="llm_fallback",
                confidence=0.5,
                evidence="无文档答案，需 LLM 推理",
            )

    # 匹配详解
    if q_num in explanation_map:
        sq.explanation_line_ids = explanation_map[q_num]
        sq.explanation_provenance = SourceProvenance(
            field="explanation",
            source="document_inline_explanation",
            confidence=1.0,
            evidence="题后详解标记",
        )
        sq.explanation = _extract_explanation_text(doc, explanation_map[q_num])
    else:
        sq.explanation_provenance = SourceProvenance(
            field="explanation",
            source="llm_fallback",
            confidence=0.5,
            evidence="无文档详解，需 LLM 推理",
        )


def _find_answer_table_line(doc: L1Document, q_num: str) -> list[str]:
    """找到答案表中对应题号的行 ID。"""
    result: list[str] = []
    in_answer_section = False

    for line in doc.lines:
        if _ANSWER_SECTION_RE.search(line.text):
            in_answer_section = True
            continue
        if not in_answer_section:
            continue

        if _ANSWER_TABLE_MARKER_RE.search(line.text):
            pattern = rf"[（(]\s*{re.escape(q_num)}\s*[）)]"
            if not re.search(pattern, line.text):
                continue
            result.append(line.line_id)

    return result


def _find_inline_answer(doc: L1Document, q_num: str) -> dict | None:
    """找到题后的内联答案。"""
    found_q = False
    for line in doc.lines:
        # 匹配 (1) 或 1. 格式的题号
        m = re.match(rf"^[（(]\s*{re.escape(q_num)}\s*[）)]", line.text)
        if not m:
            m = re.match(rf"^\s*{re.escape(q_num)}\s*[.、．]", line.text)
        if m:
            found_q = True
            continue

        if found_q:
            answer_m = _INLINE_ANSWER_RE.search(line.text)
            if answer_m:
                return {"text": answer_m.group(1).strip(), "line_id": line.line_id}

            # 遇到下一题时停止
            next_q_paren = re.match(r"^[（(]\s*\d{1,3}\s*[）)]", line.text)
            next_q_dot = re.match(r"^\s*\d{1,3}\s*[.、．]", line.text)
            if next_q_paren or next_q_dot:
                break

    return None


def _extract_explanation_text(doc: L1Document, line_ids: list[str]) -> str:
    """提取详解文本。"""
    parts: list[str] = []
    for lid in line_ids:
        for line in doc.lines:
            if line.line_id == lid:
                text = _INLINE_EXPLANATION_RE.sub("", line.text).strip()
                if text:
                    parts.append(text)
                break
    return " ".join(parts)

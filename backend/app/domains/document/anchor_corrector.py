"""锚点校验器 — L2Annotation 行号 → CorrectedAnchor → 回写 question。

职责边界（2026-08-17 对抗性审查后收紧）：
- LLM 负责判断题目、选项、答案、详解的行号范围；
- 代码只校验行号是否有效、首行是否指向正确内容（题号/选项标签）；
- 校验失败返回 retry，由 simple_pipeline 的 LLM 重试链路处理；
- 不再吸附无效行号、不反推题干、不扩展/收缩 stem 范围。

保存 llm_anchors（原始）和 corrected_anchors（校验后）两份镜像。
"""

from __future__ import annotations

import logging
import re

from app.domains.document.schemas_l1 import L1Document, L1Line
from app.domains.document.schemas_l2 import CorrectedAnchor, L2DocumentAnnotation
from app.domains.document.semantic_anchor import (
    StemResolution,
    find_marker,
    resolve_composite_stem_range,
    resolve_stem_range,
)

logger = logging.getLogger(__name__)

# 题号模式（行首）。排除小数和 LaTeX 续行（如 0.\end{aligned}）。
# 兼容 VL 输出的转义点（如 "16\. 下列..."）：\\? 匹配可选的反斜杠。
_QUESTION_NUMBER_RE = re.compile(
    r"^(\s*)(\d{1,3})\s*\\?[.、．]"
    r"(?!\d+(?:\s*[+\-*/=×÷xX\\]|$))"
    r"(?!\\)"
)
# 括号题号
_PAREN_QUESTION_RE = re.compile(r"^(\s*)[（(]\s*(\d{1,3})\s*[）)]\s*")
# 占位题号行（如 "（1）（集团校自创题）"）：不是完整题目。
_PLACEHOLDER_QUESTION_RE = re.compile(
    r"^\s*[（(]\s*\d{1,3}\s*[）)]\s*[（(]集团(?:校)?自创题[）)]\s*$"
)
# 选项标签（（A） 或 (A) 或 A.），七选五等题型允许 A-G。
_OPTION_LABEL_RE = re.compile(r"^[（(]?\s*([A-G])\s*[）)]?\s*[.、．]?\s*")
_STRICT_OPTION_LABEL_RE = re.compile(
    r"^[\uFF08(]?\s*([A-G])\s*(?:"
    r"[\uFF09)]\s*|[.\u3001\uFF0E]\s*|"
    r"\s+(?=[0-9$\\[{(+-])|$"
    r")"
)
# 答案区起点（精确）：独立"参考答案"/"答案"标题行或"【答案】"标题行。
_ANSWER_SECTION_START_RE = re.compile(
    r"(?:^|[\s，。；：])(?:参考答案|答案|Answer\s*Key)(?:\s*[:：]|$)|^【答案】\s*$",
    re.IGNORECASE,
)


def _is_placeholder_question_line(text: str) -> bool:
    """判断是否为仅含“集团校自创题”标记的占位题号行。"""
    return bool(_PLACEHOLDER_QUESTION_RE.match(text or ""))


def _answer_section_start_order(doc: L1Document) -> int:
    """返回参考答案区的第一个 order；无答案区时返回无穷大。

    只把真正独立的"参考答案/答案"标题行视为答案区起点。
    "三、解答题"标题后是解答题题目本体，不是答案区，不能作为边界
    （否则数学/物理解答题题干会被误判"位于答案区"而全部拒绝）。
    """
    for line in doc.lines:
        if _ANSWER_SECTION_START_RE.search(line.text):
            return line.order
    return float("inf")


def _is_after_answer_section(line: L1Line | None, stop_order: int) -> bool:
    """判断行是否位于参考答案区之后。"""
    return line is not None and line.order >= stop_order


def _extract_question_number(text: str) -> int | None:
    """从行文本中提取题号数字。"""
    m = _QUESTION_NUMBER_RE.match(text)
    if m:
        return int(m.group(2))
    m = _PAREN_QUESTION_RE.match(text)
    if m:
        return int(m.group(2))
    return None


def _build_question_start_map(doc: L1Document) -> dict[int, str]:
    """构建题号 → 行 ID 映射，供 simple_pipeline 判断漏题后触发重试。

    保留第一性原理边界：这里不修正 LLM 锚点，只用于判断文档是否存在 LLM 漏标的题号。
    参考答案区之后的行不参与，避免 "4.【分析】"、"37.B" 被误认为题目。
    """
    stop_order = _answer_section_start_order(doc)
    best: dict[int, tuple[int, int, str]] = {}
    for line in doc.lines:
        if line.order >= stop_order:
            break
        if _is_placeholder_question_line(line.text):
            continue
        m_paren = _PAREN_QUESTION_RE.match(line.text)
        m_dot = _QUESTION_NUMBER_RE.match(line.text)
        if not m_paren and not m_dot:
            continue
        q_num = int((m_dot or m_paren).group(2))
        marker_end = (m_dot or m_paren).end()
        rest = line.text[marker_end:].strip()
        bare = not rest
        if m_dot:
            priority = 3 if bare else 1
        else:
            priority = 2 if bare else 0
        current = best.get(q_num)
        if current is None or (priority, -line.order) > (current[0], -current[1]):
            best[q_num] = (priority, line.order, line.line_id)
    return {q_num: lid for q_num, (_, _, lid) in best.items()}


def _validate_stem_anchor(
    *,
    llm_line_ids: list[str],
    valid_ids: set[str],
    line_by_id: dict[str, L1Line],
    question_number: str | None,
    stop_order: int,
    is_composite: bool = False,
    has_shared_material: bool = False,
) -> CorrectedAnchor:
    """只校验 stem：首行必须是当前题号，且不得位于答案区。

    综合题（is_composite=True 或 has_shared_material=True）豁免首行题号校验：
    材料首行通常不含题号，只要求行号有效、不在答案区。
    """
    valid_ids_list = [lid for lid in llm_line_ids if lid in valid_ids]
    if not valid_ids_list:
        return CorrectedAnchor(
            field="stem",
            llm_line_ids=llm_line_ids,
            corrected_line_ids=[],
            anchor_status="retry",
            validation_passed=False,
            evidence="LLM 未输出有效题干行号，需重新标注",
            question_number=question_number,
        )

    first_line = line_by_id.get(valid_ids_list[0])
    if _is_after_answer_section(first_line, stop_order):
        return CorrectedAnchor(
            field="stem",
            llm_line_ids=llm_line_ids,
            corrected_line_ids=[],
            anchor_status="retry",
            validation_passed=False,
            evidence="题干首行位于答案区，需重新标注",
            question_number=question_number,
        )

    # 综合题豁免：材料首行通常不含题号，只要求行号有效、不在答案区
    if is_composite or has_shared_material:
        return CorrectedAnchor(
            field="stem",
            llm_line_ids=llm_line_ids,
            corrected_line_ids=valid_ids_list,
            anchor_status="exact",
            validation_passed=True,
            evidence=f"综合题校验通过：行号有效，首行不在答案区",
            question_number=question_number,
        )

    matched = _extract_question_number(first_line.text) if first_line else None
    if matched is None or str(matched) != question_number:
        return CorrectedAnchor(
            field="stem",
            llm_line_ids=llm_line_ids,
            corrected_line_ids=[],
            anchor_status="retry",
            validation_passed=False,
            evidence=(
                f"题干首行不是题目 {question_number} 的题号行，需重新标注"
            ),
            question_number=question_number,
        )

    return CorrectedAnchor(
        field="stem",
        llm_line_ids=llm_line_ids,
        corrected_line_ids=valid_ids_list,
        anchor_status="exact",
        validation_passed=True,
        evidence=f"校验通过：首行为题目 {question_number} 题号行",
        question_number=question_number,
    )


def _validate_option_anchor(
    *,
    label: str,
    llm_line_ids: list[str],
    valid_ids: set[str],
    line_by_id: dict[str, L1Line],
    question_number: str | None,
    stop_order: int,
) -> CorrectedAnchor:
    """只校验选项：首行必须是当前标签的选项行，且不得位于答案区。"""
    valid_ids_list = [lid for lid in llm_line_ids if lid in valid_ids]
    if not valid_ids_list:
        return CorrectedAnchor(
            field=f"option_{label}",
            llm_line_ids=llm_line_ids,
            corrected_line_ids=[],
            anchor_status="retry",
            validation_passed=False,
            evidence=f"选项 {label} 未输出有效行号，需重新标注",
            question_number=question_number,
        )

    first_line = line_by_id.get(valid_ids_list[0])
    if _is_after_answer_section(first_line, stop_order):
        return CorrectedAnchor(
            field=f"option_{label}",
            llm_line_ids=llm_line_ids,
            corrected_line_ids=[],
            anchor_status="retry",
            validation_passed=False,
            evidence=f"选项 {label} 首行位于答案区，需重新标注",
            question_number=question_number,
        )

    m = _STRICT_OPTION_LABEL_RE.match(first_line.text) if first_line else None
    if not m or m.group(1) != label:
        return CorrectedAnchor(
            field=f"option_{label}",
            llm_line_ids=llm_line_ids,
            corrected_line_ids=[],
            anchor_status="retry",
            validation_passed=False,
            evidence=f"选项 {label} 首行不是匹配的选项标签行，需重新标注",
            question_number=question_number,
        )

    return CorrectedAnchor(
        field=f"option_{label}",
        llm_line_ids=llm_line_ids,
        corrected_line_ids=valid_ids_list,
        anchor_status="exact",
        validation_passed=True,
        evidence=f"校验通过：首行为选项 {label} 标签行",
        question_number=question_number,
    )


def _resolve_stem_by_markers_fallback(
    question,
    doc: L1Document,
    *,
    stop_order: int,
    question_start_map: dict[int, str],
) -> StemResolution | None:
    """marker 简单兜底：stem_line_ids 为空但 LLM 给了 stem marker 时定位行号。

    2026-08-25 数学 Q1-3（P10 批次）：LLM 漏给 stem_line_ids（空列表）但
    marker 完整；resolve_stem_range 因 marker 与 L1 文本形态差异（LaTeX
    vs native 打散符号）可能返回 None → 题干切片为空 → stem_empty 丢弃。
    此处直接用 find_marker 定位 start 行，end 取 end_marker / 下一题边界 /
    答案区起点中的较早者（与 resolve_stem_range 的确定性边界一致）。
    仅作为最后兜底，不改变正常路径行为。
    """
    start_marker = (question.stem_start_marker or "").strip()
    if not start_marker:
        return None
    start_match = find_marker(
        start_marker,
        doc.lines,
        stop_order=stop_order,
        question_number=question.question_number,
    )
    if start_match is None:
        return None
    line_by_id = {line.line_id: line for line in doc.lines}
    start_line = line_by_id.get(start_match.line_id)
    if start_line is None:
        return None

    end_order = stop_order - 1 if stop_order != float("inf") else None
    end_marker = (question.stem_end_marker or "").strip()
    if end_marker:
        end_match = find_marker(
            end_marker,
            doc.lines,
            start_order=start_line.order,
            stop_order=stop_order,
            question_number=question.question_number,
        )
        if end_match is not None:
            end_line = line_by_id.get(end_match.line_id)
            if end_line is not None and end_line.order >= start_line.order:
                end_order = end_line.order if end_order is None else min(end_order, end_line.order)
    # 下一题边界（文档顺序上位于当前题之后的题号行）
    for qnum, line_id in question_start_map.items():
        if str(qnum) == str(question.question_number or ""):
            continue
        line = line_by_id.get(line_id)
        if line is not None and line.order > start_line.order:
            end_order = line.order - 1 if end_order is None else min(end_order, line.order - 1)

    if end_order is None or end_order < start_line.order:
        return None
    line_ids = [
        line.line_id
        for line in doc.lines
        if start_line.order <= line.order <= end_order
    ]
    if not line_ids:
        return None
    return StemResolution(
        line_ids=line_ids,
        status="nearest",
        confidence=0.9,
        evidence="marker-fallback (stem_line_ids empty)",
    )


def _truncate_stem_at_next_question(
    stem_line_ids: list[str],
    line_by_id: dict[str, L1Line],
    question_start_map: dict[int, str],
    current_question_number: str | None,
    stop_order: int,
) -> list[str]:
    """P0-B: 截断 stem 行号到下一题起点之前。

    防止 LLM 标注的 stem 范围包含了下一题的行（结束位置未校验）。
    边界取「文档顺序上位于当前题干起点之后最早的题号行」：
    - 常规顺序编号时等价于「下一个题号」；
    - 语法填空等行内编号 section 中，题号行可能在数节之外；
    - OCR 噪声题号（如书面表达标题拆行 "48、49"）若在文档顺序上早于
      当前题，仅按题号大小取边界会把 stem 截空（英语 Q46 作文被误丢），
      故必须按文档顺序，不按题号大小。
    """
    if not stem_line_ids:
        return stem_line_ids

    # 当前题干在文档中的起点 order
    current_orders = [
        line_by_id[lid].order
        for lid in stem_line_ids
        if lid in line_by_id
    ]
    if not current_orders:
        return stem_line_ids
    current_start = min(current_orders)

    try:
        current_qnum = int(current_question_number) if current_question_number else None
    except (ValueError, TypeError):
        current_qnum = None

    # 非数字题号（如"实验一"）：无题号序可言，保持旧行为不做截断
    # （子题行（1）（2）等小号会误作边界导致过度截断）。
    if current_qnum is None:
        return stem_line_ids

    # 边界锚点：优先当前题自己的题号行（复合题材料在前、题号行在 stem
    # 内部时，题号行不能当作下一题边界，但它仍锚定本节的起点）。
    # 无独立题号行（语法填空等行内编号）时退回题干起点。
    own_line_id = question_start_map.get(current_qnum) if current_qnum is not None else None
    own_line = line_by_id.get(own_line_id) if own_line_id else None
    anchor_order = own_line.order if own_line is not None else current_start

    # 文档顺序边界：锚点之后、且题号不小于当前题号的题号行。
    # - 题号过滤：子题行（（1）（2）等小号）不属于顶层题边界；
    # - 文档顺序过滤：OCR 噪声题号（如书面表达标题拆行 "48、49"）在文档
    #   顺序上早于当前题时，仅按题号大小取边界会把 stem 截空
    #   （英语 Q46 作文被误丢）。
    boundary_order = stop_order  # 默认：答案区起点
    for qnum, line_id in question_start_map.items():
        if current_qnum is not None and qnum <= current_qnum:
            continue
        line = line_by_id.get(line_id)
        if line is not None and line.order > anchor_order:
            boundary_order = min(boundary_order, line.order)

    # 截断：只保留 order < boundary_order 的行
    truncated = [
        lid for lid in stem_line_ids
        if lid in line_by_id and line_by_id[lid].order < boundary_order
    ]

    if len(truncated) < len(stem_line_ids):
        removed = len(stem_line_ids) - len(truncated)
        logger.info(
            "P0-B: truncated %d stem lines after next-question boundary (Q%s, boundary_order=%s)",
            removed, current_question_number, boundary_order,
        )

    # 不回退到原始列表：如果全部行都在边界之后，返回空列表（下游 quality_gate 拦截）。
    # 旧逻辑 `return truncated if truncated else stem_line_ids` 是 self-defeating 的：
    # 当 LLM 完全标错时截断为空 → 回退到原始列表 → 截断失效。
    return truncated


def correct_anchors(
    annotation: L2DocumentAnnotation,
    doc: L1Document,
) -> L2DocumentAnnotation:
    """校验 L2 标注中的行号锚点，并回写 question 字段。

    校验通过：question.stem_line_ids / options_line_ids 保留 LLM 有效行号。
    校验失败：清空对应 corrected_line_ids 并标记 retry，由重试链路修正。
    """
    valid_line_ids = {l.line_id for l in doc.lines}
    line_by_id = {l.line_id: l for l in doc.lines}
    stop_order = _answer_section_start_order(doc)
    question_start_map = _build_question_start_map(doc)

    llm_anchors: list[CorrectedAnchor] = []
    corrected_anchors: list[CorrectedAnchor] = []
    anchor_status_summary: dict[str, int] = {}

    for question in annotation.questions:
        semantic_stem = resolve_stem_range(
            question,
            doc,
            stop_order=stop_order,
            question_start_map=question_start_map,
        )
        if semantic_stem is None and (
            question.is_composite or question.shared_material_line_ids
        ):
            semantic_stem = resolve_composite_stem_range(
                question,
                doc,
                stop_order=stop_order,
                question_start_map=question_start_map,
            )
        # 2026-08-25 数学 Q1-3 兜底：语义解析失败且 LLM 未给 stem 行号但有
        # marker → 用 marker 直接定位（否则 stem 切片空 → stem_empty 丢弃）。
        if semantic_stem is None and not question.stem_line_ids:
            semantic_stem = _resolve_stem_by_markers_fallback(
                question,
                doc,
                stop_order=stop_order,
                question_start_map=question_start_map,
            )
        stem_anchor = _validate_stem_anchor(
            llm_line_ids=question.stem_line_ids,
            valid_ids=valid_line_ids,
            line_by_id=line_by_id,
            question_number=question.question_number,
            stop_order=stop_order,
            is_composite=question.is_composite,
            has_shared_material=bool(question.shared_material_line_ids),
        )
        if semantic_stem is not None:
            semantic_anchor = _validate_stem_anchor(
                llm_line_ids=semantic_stem.line_ids,
                valid_ids=valid_line_ids,
                line_by_id=line_by_id,
                question_number=question.question_number,
                stop_order=stop_order,
                is_composite=question.is_composite,
                has_shared_material=bool(question.shared_material_line_ids),
            )
            if semantic_anchor.validation_passed:
                semantic_anchor.anchor_status = semantic_stem.status
                semantic_anchor.corrected_line_ids = semantic_stem.line_ids
                semantic_anchor.evidence = semantic_stem.evidence
                stem_anchor = semantic_anchor
        llm_anchors.append(CorrectedAnchor(
            field="stem",
            llm_line_ids=question.stem_line_ids,
            corrected_line_ids=question.stem_line_ids,
            anchor_status="llm_raw",
            question_number=question.question_number,
        ))
        corrected_anchors.append(stem_anchor)
        question.stem_line_ids = stem_anchor.corrected_line_ids

        # P0-B: stem 结束位置校验 — 截断到下一题起点之前。
        # 语义锚点在有 marker 时已计算下一题边界，但 LLM 裸行号路径不做此检查。
        # 这里统一后处理：无论 stem 来自语义锚点还是 LLM 原始行号，
        # 都不能包含下一题的行。
        # 例外（2026-08-25 数学 Q1-3）：marker 兜底来源的行号已按
        # start/end marker + 下一题边界精确切片，P0-B 截断（boundary_order
        # 取自 question_start_map）反而可能把合法题干行误截为空 →
        # stem_empty。兜底来源跳过截断。
        is_marker_fallback = bool(
            stem_anchor.evidence and "marker-fallback" in stem_anchor.evidence
        )
        truncated_ids = question.stem_line_ids
        if not is_marker_fallback:
            truncated_ids = _truncate_stem_at_next_question(
                question.stem_line_ids,
                line_by_id,
                question_start_map,
                question.question_number,
                stop_order,
            )
        question.stem_line_ids = truncated_ids
        # 同步 stem_anchor.corrected_line_ids，避免下游（content_slicer 合并、
        # pipeline 序列化、配图关联）使用未截断的行号。
        stem_anchor.corrected_line_ids = truncated_ids

        corrected_options: dict[str, list[str]] = {}
        for opt_label, opt_line_ids in question.options_line_ids.items():
            opt_anchor = _validate_option_anchor(
                label=opt_label,
                llm_line_ids=opt_line_ids,
                valid_ids=valid_line_ids,
                line_by_id=line_by_id,
                question_number=question.question_number,
                stop_order=stop_order,
            )
            llm_anchors.append(CorrectedAnchor(
                field=f"option_{opt_label}",
                llm_line_ids=opt_line_ids,
                corrected_line_ids=opt_line_ids,
                anchor_status="llm_raw",
                question_number=question.question_number,
            ))
            corrected_anchors.append(opt_anchor)
            corrected_options[opt_label] = opt_anchor.corrected_line_ids
        question.options_line_ids = corrected_options

        # Remove option lines from stem (LLM may have over-included)
        all_option_line_ids = set()
        for opt_ids in corrected_options.values():
            all_option_line_ids.update(opt_ids)
        if all_option_line_ids:
            original_stem_len = len(question.stem_line_ids)
            question.stem_line_ids = [
                lid for lid in question.stem_line_ids
                if lid not in all_option_line_ids
            ]
            if len(question.stem_line_ids) != original_stem_len:
                logger.info(
                    "Removed %d option lines from stem for Q%s",
                    original_stem_len - len(question.stem_line_ids),
                    question.question_number,
                )

        status = stem_anchor.anchor_status
        anchor_status_summary[status] = anchor_status_summary.get(status, 0) + 1

    annotation.llm_anchors = llm_anchors
    annotation.corrected_anchors = corrected_anchors
    annotation.anchor_status_summary = anchor_status_summary

    logger.info(
        "anchor_validation questions=%d anchors=%d summary=%s",
        len(annotation.questions),
        len(corrected_anchors),
        anchor_status_summary,
    )

    return annotation

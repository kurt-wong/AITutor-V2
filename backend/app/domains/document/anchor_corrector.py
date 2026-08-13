"""
锚点校正器 — L2Annotation 行号 → CorrectedAnchor → 回写 question。

LLM 输出的行号经过代码校正后才能用于切片。
校正规则按 T3_IMPLEMENTATION.md §4.3：
1. 题号起点：吸附到最近的题号标记
2. 选项边界：按选项标签校正
3. 答案/详解边界：吸附到答案表、【答案】、【详解】标记
4. nearest 必须经过内容校验；无稳定标记返回 retry

校正后回写 question.stem_line_ids / options_line_ids，
保存 llm_anchors（原始）和 corrected_anchors（校正后）两份镜像。

详见 Docs/01_Product/T3_IMPLEMENTATION.md §4-8 Task 1.3。
"""

from __future__ import annotations

import logging
import re

from app.domains.document.schemas_l1 import L1Document, L1Line
from app.domains.document.schemas_l2 import CorrectedAnchor, L2DocumentAnnotation

logger = logging.getLogger(__name__)

# 题号模式（行首）。排除小数和 LaTeX 续行（如 0.\end{aligned}）。
_QUESTION_NUMBER_RE = re.compile(
    r"^(\s*)(\d{1,3})\s*[.、．](?!\d)(?!\\)"
)
# 括号题号
_PAREN_QUESTION_RE = re.compile(r"^(\s*)[（(]\s*(\d{1,3})\s*[）)]\s*")
# 选项标签（（A） 或 (A) 或 A.）
_OPTION_LABEL_RE = re.compile(r"^[（(]?\s*([A-D])\s*[）)]?\s*[.、．]?\s*")
# 答案区标记
_ANSWER_SECTION_RE = re.compile(r"(答案|Answer|参考答案|Answer\s*Key)", re.IGNORECASE)


def correct_anchors(
    annotation: L2DocumentAnnotation,
    doc: L1Document,
) -> L2DocumentAnnotation:
    """校正 L2 标注中的行号锚点，并回写 question 字段。

    校正后 question.stem_line_ids / options_line_ids 被替换为 corrected_line_ids，
    原始 LLM 输出保存在 llm_anchors 中。

    Args:
        annotation: LLM 标注结果
        doc: L1 文档

    Returns:
        更新后的 L2DocumentAnnotation
    """
    valid_line_ids = {l.line_id for l in doc.lines}
    line_by_id = {l.line_id: l for l in doc.lines}

    question_start_map = _build_question_start_map(doc)
    # 全局选项表用于跨题校正（当 LLM 指错题时吸附到正确题的选项）
    global_option_map = _build_option_label_map(doc)

    llm_anchors: list[CorrectedAnchor] = []
    corrected_anchors: list[CorrectedAnchor] = []
    anchor_status_summary: dict[str, int] = {}

    for question in annotation.questions:
        # 校正 stem
        stem_anchor = _correct_field_anchor(
            field="stem",
            llm_line_ids=question.stem_line_ids,
            valid_ids=valid_line_ids,
            line_by_id=line_by_id,
            question_start_map=question_start_map,
            question_number=question.question_number,
        )
        llm_anchors.append(CorrectedAnchor(
            field="stem",
            llm_line_ids=question.stem_line_ids,
            corrected_line_ids=question.stem_line_ids,
            anchor_status="llm_raw",
            question_number=question.question_number,
        ))
        corrected_anchors.append(stem_anchor)
        question.stem_line_ids = stem_anchor.corrected_line_ids

        # 构建本题的选项行范围（使用校正后的 stem 位置）
        q_option_map = _build_per_question_option_map(
            question, doc, line_by_id, global_option_map
        )

        # 校正 options（使用 per-question map）
        corrected_options: dict[str, list[str]] = {}
        for opt_label, opt_line_ids in question.options_line_ids.items():
            opt_anchor = _correct_option_anchor(
                label=opt_label,
                llm_line_ids=opt_line_ids,
                valid_ids=valid_line_ids,
                line_by_id=line_by_id,
                option_label_map=q_option_map,
                question_number=question.question_number,
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
        # 回写 question
        question.options_line_ids = corrected_options

        # 统计 anchor_status（只统计 stem）
        status = stem_anchor.anchor_status
        anchor_status_summary[status] = anchor_status_summary.get(status, 0) + 1

    annotation.llm_anchors = llm_anchors
    annotation.corrected_anchors = corrected_anchors
    annotation.anchor_status_summary = anchor_status_summary

    logger.info(
        "anchor_correction questions=%d anchors=%d summary=%s",
        len(annotation.questions),
        len(corrected_anchors),
        anchor_status_summary,
    )

    return annotation


def _build_question_start_map(doc: L1Document) -> dict[int, str]:
    """构建题号 → 行 ID 的映射。支持 (1) 和 1. 两种格式。"""
    result: dict[int, str] = {}
    for line in doc.lines:
        for pattern in [_PAREN_QUESTION_RE, _QUESTION_NUMBER_RE]:
            m = pattern.match(line.text)
            if m:
                q_num = int(m.group(2))
                if q_num not in result:
                    result[q_num] = line.line_id
                break
    return result


def _build_option_label_map(doc: L1Document) -> dict[str, str]:
    """构建选项标签 → 行 ID 的全局映射。"""
    result: dict[str, str] = {}
    for line in doc.lines:
        m = _OPTION_LABEL_RE.match(line.text)
        if m:
            label = m.group(1)
            if label not in result:
                result[label] = line.line_id
    return result


def _build_per_question_option_map(
    question, doc: L1Document, line_by_id: dict, global_map: dict
) -> dict[str, str]:
    """构建 per-question 的选项标签 → 行 ID 映射。

    策略：从 question.stem_line_ids 的起始位置开始，
    向后搜索直到下一个题号标记，收集此范围内的选项。
    """
    # 找到本题起始行的 order
    stem_order = 0
    if question.stem_line_ids:
        first_line = line_by_id.get(question.stem_line_ids[0])
        if first_line:
            stem_order = first_line.order

    # 找到下一题的起始 order
    next_q_order = float("inf")
    for line in doc.lines:
        if line.order <= stem_order:
            continue
        if _PAREN_QUESTION_RE.match(line.text) or _QUESTION_NUMBER_RE.match(line.text):
            next_q_order = line.order
            break

    # 收集本题范围内的选项
    result: dict[str, str] = {}
    for line in doc.lines:
        if line.order < stem_order or line.order >= next_q_order:
            continue
        m = _OPTION_LABEL_RE.match(line.text)
        if m:
            label = m.group(1)
            if label not in result:
                result[label] = line.line_id

    # 不回退到全局 map，避免跨题选项污染
    return result


def _has_stable_marker(line: L1Line) -> bool:
    """检查行是否有稳定锚点标记（题号或选项标签）。"""
    if _QUESTION_NUMBER_RE.match(line.text):
        return True
    if _PAREN_QUESTION_RE.match(line.text):
        return True
    if _OPTION_LABEL_RE.match(line.text):
        return True
    return False


def _extract_question_number(text: str) -> int | None:
    """从行文本中提取题号数字。"""
    m = _QUESTION_NUMBER_RE.match(text)
    if m:
        return int(m.group(2))
    m = _PAREN_QUESTION_RE.match(text)
    if m:
        return int(m.group(2))
    return None


def _correct_field_anchor(
    *,
    field: str,
    llm_line_ids: list[str],
    valid_ids: set[str],
    line_by_id: dict[str, L1Line],
    question_start_map: dict[int, str],
    question_number: str | None = None,
) -> CorrectedAnchor:
    """校正单个字段的锚点。

    anchor_status 规则：
    - exact: 首行精确匹配题号/选项标记
    - nearest: 行号有效 + 同范围内有稳定标记
    - retry: 行号有效但无稳定标记（LLM 粗定位偏移）
    - missing: 行号为空或全部无效
    """
    if not llm_line_ids:
        return CorrectedAnchor(
            field=field,
            llm_line_ids=[],
            corrected_line_ids=[],
            anchor_status="missing",
            validation_passed=False,
            evidence="LLM 未输出行号",
            question_number=question_number,
        )

    valid_ids_list = [lid for lid in llm_line_ids if lid in valid_ids]
    if not valid_ids_list:
        return CorrectedAnchor(
            field=field,
            llm_line_ids=llm_line_ids,
            corrected_line_ids=[],
            anchor_status="missing",
            validation_passed=False,
            evidence=f"所有行号无效: {llm_line_ids}",
            question_number=question_number,
        )

    # 检查首行是否精确匹配题号标记（(1) 和 1. 两种格式）
    # 关键：必须校验该题号是否属于当前题目，不能跨题 exact
    first_line = line_by_id.get(valid_ids_list[0])
    if first_line and (
        _QUESTION_NUMBER_RE.match(first_line.text)
        or _PAREN_QUESTION_RE.match(first_line.text)
    ):
        matched_num = _extract_question_number(first_line.text)
        if question_number and matched_num and str(matched_num) != question_number:
            # 首行题号与当前题目不符 → 跨题，不能 exact，落入后续逻辑
            pass
        else:
            return CorrectedAnchor(
                field=field,
                llm_line_ids=llm_line_ids,
                corrected_line_ids=valid_ids_list,
                anchor_status="exact",
                validation_passed=True,
                evidence=f"精确匹配题号标记: {first_line.text[:30]}",
                question_number=question_number,
            )

    # 尝试修正到当前题目的起始行（question_start_map）
    if question_number and question_number.isdigit():
        target_qnum = int(question_number)
        if target_qnum in question_start_map:
            target_line_id = question_start_map[target_qnum]
            if target_line_id in valid_ids:
                return CorrectedAnchor(
                    field=field,
                    llm_line_ids=llm_line_ids,
                    corrected_line_ids=[target_line_id],
                    anchor_status="nearest",
                    validation_passed=True,
                    evidence=f"修正到题目 {question_number} 起始行: {line_by_id[target_line_id].text[:30]}",
                    question_number=question_number,
                )
            else:
                # 目标行不在有效行中 → retry
                return CorrectedAnchor(
                    field=field,
                    llm_line_ids=llm_line_ids,
                    corrected_line_ids=[],
                    anchor_status="retry",
                    validation_passed=False,
                    evidence=f"题目 {question_number} 起始行 {target_line_id} 不在 LLM 行号中",
                    question_number=question_number,
                )

    # 检查有效行中是否有稳定标记（且标记属于当前题目）
    for lid in valid_ids_list:
        line = line_by_id.get(lid)
        if line and _has_stable_marker(line):
            # 验证该标记是否属于当前题目
            marker_num = _extract_question_number(line.text)
            if question_number and marker_num and str(marker_num) != question_number:
                # 稳定标记属于其他题目 → retry
                return CorrectedAnchor(
                    field=field,
                    llm_line_ids=llm_line_ids,
                    corrected_line_ids=valid_ids_list,
                    anchor_status="retry",
                    validation_passed=False,
                    evidence=f"稳定标记属于题目 {marker_num}，非当前题目 {question_number}",
                    question_number=question_number,
                )
            return CorrectedAnchor(
                field=field,
                llm_line_ids=llm_line_ids,
                corrected_line_ids=valid_ids_list,
                anchor_status="nearest",
                validation_passed=True,
                evidence=f"吸附到稳定标记: {line.text[:30]}",
                question_number=question_number,
            )

    # 行号有效但无稳定标记 → retry（不是 nearest）
    return CorrectedAnchor(
        field=field,
        llm_line_ids=llm_line_ids,
        corrected_line_ids=valid_ids_list,
        anchor_status="retry",
        validation_passed=False,
        evidence="行号有效但无稳定锚点标记，需重新标注",
        question_number=question_number,
    )


def _correct_option_anchor(
    *,
    label: str,
    llm_line_ids: list[str],
    valid_ids: set[str],
    line_by_id: dict[str, L1Line],
    option_label_map: dict[str, str],
    question_number: str | None = None,
) -> CorrectedAnchor:
    """校正选项锚点。"""
    if not llm_line_ids:
        return CorrectedAnchor(
            field=f"option_{label}",
            llm_line_ids=[],
            corrected_line_ids=[],
            anchor_status="missing",
            validation_passed=False,
            evidence=f"LLM 未输出选项 {label} 行号",
            question_number=question_number,
        )

    valid_ids_list = [lid for lid in llm_line_ids if lid in valid_ids]
    if not valid_ids_list:
        return CorrectedAnchor(
            field=f"option_{label}",
            llm_line_ids=llm_line_ids,
            corrected_line_ids=[],
            anchor_status="missing",
            validation_passed=False,
            evidence=f"选项 {label} 所有行号无效",
            question_number=question_number,
        )

    # 检查首行是否精确匹配选项标签
    # 关键：必须验证该行在当前题目的 per-question map 范围内，不能跨题 exact
    first_line = line_by_id.get(valid_ids_list[0])
    if first_line:
        m = _OPTION_LABEL_RE.match(first_line.text)
        if m and m.group(1) == label:
            # 验证该行是否在当前题目的选项范围内
            if valid_ids_list[0] in option_label_map.values():
                return CorrectedAnchor(
                    field=f"option_{label}",
                    llm_line_ids=llm_line_ids,
                    corrected_line_ids=valid_ids_list,
                    anchor_status="exact",
                    validation_passed=True,
                    evidence=f"精确匹配选项 {label}: {first_line.text[:30]}",
                    question_number=question_number,
                )
            else:
                # 跨题选项，不能 exact → 落入 nearest/missing 逻辑
                pass

    # 尝试吸附到正确标签的选项行：替换错误行，不是追加
    if label in option_label_map:
        target_id = option_label_map[label]
        # 如果 LLM 给的行不是目标行，替换为正确行
        if target_id not in valid_ids_list:
            corrected_ids = [target_id]
        else:
            corrected_ids = valid_ids_list
        return CorrectedAnchor(
            field=f"option_{label}",
            llm_line_ids=llm_line_ids,
            corrected_line_ids=corrected_ids,
            anchor_status="nearest",
            validation_passed=True,
            evidence=f"吸附到选项 {label}: {line_by_id[target_id].text[:30]}",
            question_number=question_number,
        )

    # 无对应标签的选项行 → retry
    return CorrectedAnchor(
        field=f"option_{label}",
        llm_line_ids=llm_line_ids,
        corrected_line_ids=valid_ids_list,
        anchor_status="retry",
        question_number=question_number,
        validation_passed=False,
        evidence=f"选项 {label} 无匹配的选项标记行",
    )

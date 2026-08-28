"""
内容切片器 — CorrectedAnchor + L1 原文 → SlicedQuestion。

用校正后锚点从 L1 切片 stem/options，代码切片，不依赖 LLM 抄写。
遵守 V1_LESSONS 3.1（信息零损耗）。

详见 Docs/01_Product/T3_IMPLEMENTATION.md §8 Task 1.4。
"""

from __future__ import annotations

import logging
import re

from app.domains.document.schemas_l1 import L1Document, L1Line
from app.domains.document.schemas_l2 import (
    CorrectedAnchor,
    L2DocumentAnnotation,
    L2QuestionAnnotation,
    SlicedQuestion,
)

logger = logging.getLogger(__name__)

# LLM 题型枚举归一化：不同 LLM 可能输出不同变体，统一到 canonical 值
_QUESTION_TYPE_CANONICAL = {
    "fill_blank": "fill_in",
    "fill_in_blank": "fill_in",
    "fill_in_the_blank": "fill_in",
    "填空": "fill_in",
    "填空题": "fill_in",
    "fill": "fill_in",
    "choice": "single_choice",
    "single_choice": "single_choice",
    "选择": "single_choice",
    "选择题": "single_choice",
    "单选": "single_choice",
    "单选题": "single_choice",
    "单项选择": "single_choice",
    "单项选择题": "single_choice",
    "多选": "multiple_choice",
    "multiple_choice": "multiple_choice",
    "多选题": "multiple_choice",
    "多项选择": "multiple_choice",
    "true_false": "true_false",
    "判断题": "true_false",
    "short_answer": "short_answer",
    "简答题": "short_answer",
    "解答题": "short_answer",
    "计算题": "short_answer",
    "实验题": "short_answer",
    "实验": "short_answer",
    "实验探究": "short_answer",
    "探究题": "short_answer",
    "experiment": "short_answer",
    "reading_expression": "short_answer",  # 英语阅读表达
    "word_fill": "fill_in",
    "vocabulary_fill": "fill_in",
    "词汇填空": "fill_in",
    "选词填空": "fill_in",
    "cloze": "single_choice",  # 完形填空：每个空格本质上是单选
    "reading": "single_choice",  # 阅读理解
    "seven_to_five": "single_choice",  # 七选五
    "grammar_fill": "fill_in",  # 语法填空
}


def _canonical_question_type(qt: str) -> str:
    """将 LLM 输出的题型归一化为 canonical 枚举。"""
    return _QUESTION_TYPE_CANONICAL.get(qt, qt)


# 填空位结构化标记：空位统一为 〔N〕（入库），前端渲染为高亮，不与其他
# 普通数字混淆（P4E.1，2026-08-28）。详见 slice_questions 调用处。
# 文本科目（英语/语文/历史/政治/地理）材料填空位为裸数字（完形 1、2、3），
# 启用孤立数字替换；数理化填空位为下划线/空括号，数字密集，不启用孤立
# 数字替换（避免误标普通数字），仅处理显式 {11} / （12） 标记。
_TEXT_SUBJECTS = frozenset({"英语", "语文", "历史", "政治", "地理"})


def _mark_blank_positions(
    stem: str,
    sub_qnos: list[str],
    subject: str | None = None,
) -> str:
    """把题干/材料中的填空位标记为结构化 〔N〕。

    规则（2026-08-28，P4E.1）：
    1. 显式标记 `{11}` / `（12）` / `(37)` → `〔11〕`（所有科目，本身就是填空位标记）
    1.5 下划线空位 `____37____` → `〔37〕`（所有科目；native L1 保留
        下划线形式，PPSV3 文本层常丢下划线变裸数字/粘连，如 `_40Orthe`，
        靠规则 2 兜底。2026-08-28 LOG v6.44 补）
    2. 孤立数字 ∈ 子题 qno 集合 → `〔N〕`（仅文本科目；数理化填空位为
       下划线/空括号，数字密集，不启用避免误标普通数字）
    3. `______` / `（　　）` 等原样保留（数理化填空位）

    前端读到 〔N〕 渲染为高亮空位标记，无需猜测。
    """
    text = stem or ""
    # 规则 1：显式填空位标记（{11} / （12） / (37)）
    text = re.sub(r"\{(\d+)\}", r"〔\1〕", text)
    text = re.sub(r"[（(](\d+)[）)]", r"〔\1〕", text)
    # 规则 1.5：下划线空位（____37____ / __37__）→ 〔N〕（所有科目）
    text = re.sub(r"_+\s*(\d+)\s*_+", r"〔\1〕", text)
    # 规则 2：孤立数字（文本科目，且 ∈ 子题 qno）
    if subject in _TEXT_SUBJECTS and sub_qnos:
        qno_set = set(sub_qnos)

        def _repl(m: re.Match) -> str:
            n = m.group(1)
            return f"〔{n}〕" if n in qno_set else m.group(0)

        # 孤立数字：前后均非数字/百分号/〔〕（〔N〕 已是结构化标记不再处理）；
        # 允许数字后跟字母（英语 OCR 丢空格场景 "my 5was" → 〔5〕，2026-08-28
        # 修正：原排除字母导致完形 5/6/7/8/10 漏标）；排除小数（"2.5" 不替换）。
        # 文本科目才启用（数学不启用，见 _TEXT_SUBJECTS）。
        text = re.sub(
            r"(?<![〔\d%])(\d+)(?!\.\d|[\d〕])",
            _repl,
            text,
        )
    return text


def slice_questions(
    annotation: L2DocumentAnnotation,
    doc: L1Document,
) -> list[SlicedQuestion]:
    """用校正后锚点从 L1 切片题目内容。"""
    line_by_id = {l.line_id: l for l in doc.lines}
    sliced: list[SlicedQuestion] = []
    anchor_map = _build_anchor_map(annotation)

    for question in annotation.questions:
        sq = _slice_single_question(question, line_by_id, anchor_map)
        # 综合题父题答案：从子题答案汇总（格式 "(1) C (2) B ..."）。
        # P4E.1（2026-08-28）：LLM 对 fill_in/short_answer 综合题父题 answer
        # 常只给第一个子题裸值（东城英语 Q11 只给 "itself"，实际应为
        # "(11) itself (12) to (13) to stay"）→ 父题答案截断。修复：父题
        # 答案未覆盖全部子题（qno 未出现在父题答案中）时用汇总覆盖；
        # 父题已覆盖全部子题（如答案表匹配的 "（1）已有答案"、LLM 完整
        # 汇总 "(1) C (2) B ..."）保留父题（教师版答案优先，V1 3.8）。
        if (
            getattr(sq, "is_composite", False)
            and sq.sub_questions
        ):
            sub_answers = [
                f"({sub.qno}) {sub.answer}"
                for sub in sq.sub_questions
                if (sub.answer or "").strip()
            ]
            if sub_answers:
                parent_ans = (sq.answer or "").strip()
                if parent_ans:
                    covered = sum(
                        1
                        for sub in sq.sub_questions
                        if (sub.answer or "").strip()
                        and str(sub.qno) in parent_ans
                    )
                    if covered < len(sub_answers):
                        # 父题只覆盖部分子题（单值/截断）→ 用完整汇总
                        sq.answer = " ".join(sub_answers)
                else:
                    sq.answer = " ".join(sub_answers)

        # P4E.1（2026-08-28）：综合题题干/材料中的填空位标记为结构化 〔N〕，
        # 前端渲染高亮（完形 1、2、3 → 〔1〕〔2〕〔3〕；语法填空 {11} → 〔11〕；
        # 七选五 （37） → 〔37〕）。数理化填空位为下划线/空括号，原样保留。
        # 2026-08-28 补强（LOG v6.44）：① 子题 stem 同样标记（七选五子题
        # stem 以 "37The inventor" 裸数字开头，前端子题区也需要高亮）；
        # ② 空位下划线形式 `____37____`/`_40` 兜底为孤立数字（PPSV3
        # 文本层下划线丢失/粘连，native L1 保留 `____37____`）。
        if getattr(sq, "is_composite", False) and sq.sub_questions:
            qnos = [str(sub.qno) for sub in sq.sub_questions if sub.qno]
            subject = getattr(annotation, "subject", None)
            sq.stem = _mark_blank_positions(sq.stem, qnos, subject)
            for sub in (sq.sub_questions or []):
                sub_stem = getattr(sub, "stem", None)
                if sub_stem:
                    sub.stem = _mark_blank_positions(sub_stem, qnos, subject)
        sliced.append(sq)

    # Task 2.3: 共享材料题 section_id 校验
    _validate_shared_material_sections(sliced)

    # 三层安全网：共享材料题合并
    sliced = _merge_shared_material_questions(sliced, line_by_id)

    logger.info(
        "content_slicing questions=%d sliced=%d",
        len(annotation.questions),
        len(sliced),
    )

    return sliced


def _merge_shared_material_questions(
    questions: list[SlicedQuestion],
    line_by_id: dict[str, L1Line],
) -> list[SlicedQuestion]:
    """共享材料题处理。

    核心原则：是否是综合题由 LLM 通过语义、上下文、试题结构综合判断。
    代码尊重 LLM 的 is_composite 标记，不强制合并 LLM 标记为独立的题目。

    Layer 1: LLM 已标记 is_composite=True → 保留为综合题
    Layer 2: LLM 标记 is_composite=False → 保留为独立题（即使有 shared_material_line_ids）
    Layer 3: 标记疑似共享材料题供人工复查
    """
    if not questions:
        return questions

    composites: list[SlicedQuestion] = []
    independents: list[SlicedQuestion] = []
    for q in questions:
        if q.is_composite:
            composites.append(q)
        else:
            independents.append(q)

    # Layer 3: 标记有 shared_material_line_ids 的独立题供人工复查
    _mark_suspected_shared_material(independents)

    result = composites + independents
    logger.info(
        "merge_composites: llm_composites=%d independents=%d total=%d",
        len(composites),
        len(independents),
        len(result),
    )
    return result


def _merge_by_shared_material(
    questions: list[SlicedQuestion],
    line_by_id: dict[str, L1Line],
) -> list[SlicedQuestion]:
    """Layer 2: 按 shared_material_line_ids 重叠合并题目。

    规则：
    - 两个题目共享 ≥1 行材料行 → 合并为一道综合题
    - 合并后保留第一道题的 question_number 和 section_id
    - 子题元数据从各题的 question_number 和 answer 构建
    """
    if not questions:
        return []

    # 构建材料行 → 题目索引映射
    material_to_questions: dict[str, list[int]] = {}
    for idx, q in enumerate(questions):
        if q.shared_material_line_ids:
            for lid in q.shared_material_line_ids:
                material_to_questions.setdefault(lid, []).append(idx)

    # 找出需要合并的题目组（连通分量）
    n = len(questions)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    for indices in material_to_questions.values():
        if len(indices) >= 2:
            for i in range(1, len(indices)):
                union(indices[0], indices[i])

    # 按组聚合
    groups: dict[int, list[SlicedQuestion]] = {}
    for idx, q in enumerate(questions):
        root = find(idx)
        groups.setdefault(root, []).append(q)

    # 合并每组
    merged: list[SlicedQuestion] = []
    for group in groups.values():
        if len(group) == 1:
            merged.append(group[0])
        else:
            composite = _merge_question_group(group, line_by_id)
            merged.append(composite)

    return merged


def _merge_question_group(
    group: list[SlicedQuestion],
    line_by_id: dict[str, L1Line],
) -> SlicedQuestion:
    """将多道共享材料的题目合并为一道综合题。"""
    # 按 question_number 排序
    group.sort(key=lambda q: _parse_qno(q.question_number))

    primary = group[0]

    # 合并 stem_line_ids：包含共享材料 + 所有子题行号
    # 综合题的 stem 需要包含材料，前端展示时材料+题目+选项作为整体，保持连贯性。
    shared_ids = set(primary.shared_material_line_ids or [])
    all_stem_lines: list[str] = []

    # 先加入共享材料行（保持顺序）
    for lid in (primary.shared_material_line_ids or []):
        if lid not in all_stem_lines:
            all_stem_lines.append(lid)

    # 再加入各子题的 stem 行（剔除已加入的材料行）
    for q in group:
        q_stem_ids = q.stem_anchor.corrected_line_ids if q.stem_anchor else []
        for lid in q_stem_ids:
            if lid not in all_stem_lines:
                all_stem_lines.append(lid)

    # 切片合并后的 stem（材料 + 子题）
    stem = _slice_lines(all_stem_lines, line_by_id)

    # 构建子题元数据（P1-6 修复：从 L2 子题提取答案，而非 SlicedQuestion.answer（永远 None））
    from app.domains.document.schemas_l2 import L2SubQuestion
    sub_questions: list[L2SubQuestion] = []
    for q in group:
        # 优先从 L2 子题元数据提取答案（_slice_single_question 传递的 question.sub_questions）
        l2_subs = q.sub_questions or []
        if l2_subs:
            for sub in l2_subs:
                sub_questions.append(L2SubQuestion(
                    qno=sub.qno or q.question_number,
                    question_type=sub.question_type or q.question_type,
                    # 2026-08-26：选择题组综合题（共享题图）透传子题题干/选项行号
                    stem_line_ids=sub.stem_line_ids or [],
                    options_line_ids=sub.options_line_ids or {},
                    answer=sub.answer,  # L2 标注层的子题答案（LLM 输出）
                    knowledge_points=sub.knowledge_points or q.knowledge_points or [],
                    score=sub.score or q.score,
                    # P4E.1（2026-08-27）：按子题行号切片文本，链路全程保留。
                    # 此前只透传行号、不切文本，入库/API/前端丢失子题内容
                    # （完形 10 子题 A 聚合/子题无内容，LOG v6.43）。
                    stem=_slice_lines(sub.stem_line_ids or [], line_by_id),
                    options=_slice_options(sub.options_line_ids or {}, line_by_id),
                ))
        else:
            # 无 L2 子题时回退到 SlicedQuestion 层（该层已有切片文本）
            sub_questions.append(L2SubQuestion(
                qno=q.question_number,
                question_type=q.question_type,
                stem=q.stem,
                options=q.options,
                answer=q.answer,
                knowledge_points=q.knowledge_points or [],
                score=q.score,
            ))

    # 合并答案（从有答案的子题构建）
    answers = []
    for sq in sub_questions:
        if sq.answer:
            answers.append(f"({sq.qno}) {sq.answer}")
    merged_answer = " ".join(answers) if answers else None

    # 合并 knowledge_points
    all_kp = []
    for q in group:
        if q.knowledge_points:
            all_kp.extend(q.knowledge_points)
    unique_kp = list(dict.fromkeys(all_kp))  # 保序去重

    # 保留第一道带 structure_signature 的题目签名
    structure_signature = next(
        (q.structure_signature for q in group if q.structure_signature),
        None,
    )

    # 合并 confidence（取最低，默认 0.5）
    min_confidence = min(
        (q.confidence for q in group if q.confidence is not None),
        default=0.5,
    )

    # 合并 answer_line_ids
    all_answer_lines = []
    for q in group:
        for lid in (q.answer_line_ids or []):
            if lid not in all_answer_lines:
                all_answer_lines.append(lid)

    # 合并 explanation_line_ids
    all_explanation_lines = []
    for q in group:
        for lid in (q.explanation_line_ids or []):
            if lid not in all_explanation_lines:
                all_explanation_lines.append(lid)

    # 合并选项：聚合子题选项，按 label 去重
    merged_options = []
    seen_labels = set()
    for q in group:
        for opt in (q.options or []):
            label = opt.get("label", "")
            if label and label not in seen_labels:
                seen_labels.add(label)
                merged_options.append(opt)

    return SlicedQuestion(
        question_number=primary.question_number,
        question_type=primary.question_type,
        stem=stem,
        options=merged_options,
        section_id=primary.section_id,
        shared_material_line_ids=primary.shared_material_line_ids,
        difficulty=primary.difficulty,
        score=primary.score,
        knowledge_points=unique_kp,
        confidence=min_confidence,
        stem_anchor=primary.stem_anchor,
        options_anchor=None,
        corrected_anchors=primary.corrected_anchors,
        source_page=primary.source_page,
        structure_signature=structure_signature,
        is_composite=True,
        sub_questions=sub_questions,
        answer=merged_answer,
        answer_line_ids=all_answer_lines,
        explanation_line_ids=all_explanation_lines,
    )


def _parse_qno(qno: str) -> int:
    """解析题号为数字，用于排序。"""
    m = re.search(r"(\d+)", qno or "")
    return int(m.group(1)) if m else 0


def _mark_suspected_shared_material(questions: list[SlicedQuestion]) -> None:
    """Layer 3: 标记疑似共享材料题供人工复查。

    规则：
    - 有 shared_material_line_ids 但未被合并的题目
    - 多道填空题/阅读题紧邻且无独立材料
    """
    for q in questions:
        if q.is_composite:
            continue
        if q.shared_material_line_ids:
            # 有共享材料但未被合并，可能是漏合并
            if not hasattr(q, 'review_notes') or q.review_notes is None:
                q.review_notes = []
            q.review_notes.append("疑似共享材料题，请人工确认是否需要合并")


def _validate_shared_material_sections(questions: list[SlicedQuestion]) -> None:
    """保留入口；section 类型与题组边界由 LLM 负责，不再按关键词/分组告警。

    代码只负责按 LLM 给出的行号切片；若 section_id 或共享材料行号有误，
    由 simple_pipeline 的 LLM 重试链路修正，不在此处用规则猜测。
    """


def _build_anchor_map(annotation: L2DocumentAnnotation) -> dict:
    """构建 question_number → {field: CorrectedAnchor} 映射。

    使用 CorrectedAnchor.question_number 直接分组，
    不依赖顺序索引，避免 anchor 错位。
    """
    result: dict[str, dict[str, "CorrectedAnchor"]] = {}
    for anchor in annotation.corrected_anchors:
        q_num = anchor.question_number
        if not q_num:
            continue
        if q_num not in result:
            result[q_num] = {}
        result[q_num][anchor.field] = anchor
    return result


def _slice_single_question(
    question: L2QuestionAnnotation,
    line_by_id: dict[str, L1Line],
    anchor_map: dict,
) -> SlicedQuestion:
    """切片单个题目。

    共享材料并入规则（2026-08-25 修订）：
    - 综合题：stem 应包含材料 + 子题内容（前端展示需要连贯性），
      不剔除 shared_material_line_ids。
    - 独立题带共享材料（语文材料阅读/文言文等 LLM 标为独立的共享材料题）：
      P0-5 旧行为从 stem 剔除材料 → 题目失去材料上下文，无法独立使用
      （报告材料覆盖 0%）。共享材料是题目的必要上下文，独立题同样并入。
    - 无共享材料的题目：原样切片，不受影响。
    """
    material_ids = list(question.shared_material_line_ids or [])
    stem_only_ids = list(question.stem_line_ids or [])
    seen: set[str] = set()
    stem_ids: list[str] = []
    for lid in material_ids + stem_only_ids:
        if lid not in seen:
            seen.add(lid)
            stem_ids.append(lid)
    stem = _slice_lines(stem_ids, line_by_id)
    options = _slice_options(question.options_line_ids, line_by_id)

    # 获取 anchors
    q_anchors = anchor_map.get(question.question_number, {})
    stem_anchor = q_anchors.get("stem")
    # 合并所有 option anchors 为 options_anchor 列表
    option_anchors = [v for k, v in q_anchors.items() if k.startswith("option_")]
    # 构建 options_anchor: 合并所有选项锚点
    options_anchor = None
    if option_anchors:
        all_llm_ids = []
        all_corrected_ids = []
        statuses = [a.anchor_status for a in option_anchors]
        for a in option_anchors:
            all_llm_ids.extend(a.llm_line_ids)
            all_corrected_ids.extend(a.corrected_line_ids)
        if "missing" in statuses:
            worst_status = "missing"
        elif "retry" in statuses:
            worst_status = "retry"
        elif "nearest" in statuses:
            worst_status = "nearest"
        else:
            worst_status = "exact"
        options_anchor = CorrectedAnchor(
            field="options",
            llm_line_ids=all_llm_ids,
            corrected_line_ids=all_corrected_ids,
            anchor_status=worst_status,
            validation_passed=worst_status in ("exact", "nearest"),
            question_number=question.question_number,
        )

    # 全部锚点（stem + options + 子题选项汇总）
    all_anchors = [a for a in [stem_anchor] if a]
    all_anchors.extend(option_anchors)
    # 2026-08-28（LOG v6.44）：子题选项锚点校验失败（field="sub_options"）
    # 纳入 corrected_anchors，使 quality_gate._get_anchor_status 能检测到
    # retry 状态并触发 simple_pipeline 重试（此前子题行号偏移直接入库）。
    sub_options_anchor = q_anchors.get("sub_options")
    if sub_options_anchor:
        all_anchors.append(sub_options_anchor)

    # P4E.1（2026-08-27）：LLM 标记的综合题直接透传子题——此处用行号切片
    # 补齐子题 stem/options 文本（此前只透传行号，入库/API/前端丢失子题
    # 内容，完形 10 子题 A 聚合/子题无内容，LOG v6.43 链路断裂 #1）。
    from app.domains.document.schemas_l2 import L2SubQuestion
    sub_questions_out: list[L2SubQuestion] | None = None
    if question.sub_questions:
        sub_questions_out = []
        for sub in question.sub_questions:
            sub_questions_out.append(L2SubQuestion(
                qno=sub.qno,
                question_type=sub.question_type,
                stem_line_ids=sub.stem_line_ids or [],
                options_line_ids=sub.options_line_ids or {},
                answer=sub.answer,
                knowledge_points=sub.knowledge_points or [],
                score=sub.score,
                stem=_slice_lines(sub.stem_line_ids or [], line_by_id),
                options=_slice_options(sub.options_line_ids or {}, line_by_id),
            ))

    return SlicedQuestion(
        question_number=question.question_number,
        question_type=_canonical_question_type(question.question_type),
        stem=stem,
        options=options,
        section_id=question.section_id,
        shared_material_line_ids=question.shared_material_line_ids,
        difficulty=question.difficulty,
        score=question.score,
        knowledge_points=question.knowledge_points,
        confidence=question.confidence,
        stem_anchor=stem_anchor,
        options_anchor=options_anchor,
        corrected_anchors=all_anchors,
        source_page=question.source_page,
        structure_signature=question.structure_signature,
        is_composite=question.is_composite,
        # 透传 LLM 的父题答案：综合题父题 answer 可能已有值（解答题从答案表
        # 匹配）或为空（选择题组把答案写在 sub_questions 里）。answer_matcher
        # 对非综合题会覆盖此值；综合题父题答案由 slice_questions 汇总逻辑或
        # 此透传值决定。
        answer=question.answer,
        sub_questions=sub_questions_out,
    )


def _slice_lines(
    line_ids: list[str],
    line_by_id: dict[str, L1Line],
) -> str:
    """按行 ID 列表切片文本，行间用换行连接。"""
    parts: list[str] = []
    for lid in line_ids:
        line = line_by_id.get(lid)
        if line:
            parts.append(line.text)
    return "\n".join(parts)


def _slice_options(
    options_line_ids: dict[str, list[str]],
    line_by_id: dict[str, L1Line],
) -> list[dict[str, str]]:
    """切片选项，返回 [{"label": "A", "text": "..."}] 列表。

    P4E.1（2026-08-27，V1_LESSONS 3.21）：每行只处理一次（行号先去重、
    按行聚合 label 引用），行内多选项（`A.xxxB.yyyC.zzz` /
    `①②③ | B. ①②③ | C. …`）按 label 拆分归属；无行内标记的整行
    归其引用的 label。此前 `" ".join(text_parts)` 直接拼接导致
    "完形 10 个子题的 A 拼成一个 A"（LOG v6.43）。
    """
    # line_id -> [labels]（同一行被哪些 label 引用；行号去重）
    line_labels: dict[str, list[str]] = {}
    for label, lids in (options_line_ids or {}).items():
        for lid in lids:
            line_labels.setdefault(lid, []).append(label)

    per_label: dict[str, list[str]] = {}
    for lid, labels in line_labels.items():
        line = line_by_id.get(lid)
        if not line:
            continue
        inline = _inline_split_options(line.text)
        if inline:
            # 行内多选项：按拆分结果归属（忽略引用 label 上下文）
            for lab, txt in inline:
                per_label.setdefault(lab, []).append(txt)
        else:
            for lab in labels:
                per_label.setdefault(lab, []).append(
                    _strip_option_label(line.text, lab)
                )

    result: list[dict[str, str]] = []
    for label in sorted(per_label.keys()):
        text = " ".join(t for t in per_label[label] if t.strip()).strip()
        if text:
            result.append({"label": label, "text": text})
    return result


# 行内选项标签标记：A. / A． / A、 / A: / (A) 等
# 负向断言仅排除字母数字（防 "图2.B"、"xB." 误匹配）；紧凑格式
# "件B.必要" 中 B 前是中文，必须允许匹配（P4E.1 修正，V1 3.21）。
# 2026-08-28：A-D → A-G（七选五有 E/F/G 选项；PPSV3 行合并把
# "D. xxx E. yyy" 合成一行时 E/F/G 必须能被行内拆分识别，否则
# D 吞 E、E/F/G 依次错位、G 落到 section 标题，LOG v6.44）。
_INLINE_LABEL_RE = re.compile(
    r"(?<![A-Za-z0-9])([A-G])\s*[.．、:：]\s*"
)


def _inline_split_options(text: str) -> list[tuple[str, str]]:
    """行内选项拆分（V1_LESSONS 3.21，P4E.1）。

    处理 OCR/排版紧凑格式：
    - `A.充分不必要条件B.必要不充分条件C.充要条件D.既不充分也不必要条件`
      → [(A, 充分不必要条件), (B, …), (C, …), (D, …)]
    - `①②③ | B. ①②③ | C. ①②③ | D. ①②③④`（首段无 label，推断为 A）
      → [(A, ①②③), (B, ①②③), (C, ①②③), (D, ①②③④)]
    - 无多选项标记（普通题干/单选项行）→ 返回 []，整行归调用方 label。
    """
    matches = list(_INLINE_LABEL_RE.finditer(text))
    if not matches:
        return []
    parts: list[tuple[str, str]] = []
    for i, m in enumerate(matches):
        label = m.group(1)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        seg = text[start:end].strip()
        parts.append((label, seg))
    # 首段（第一个 label 前的内容）非空且无 label → 推断为 A（选项通常从 A 开始）
    first = text[: matches[0].start()].strip()
    if first:
        parts.insert(0, ("A", first))
    return parts


def _strip_option_label(text: str, label: str) -> str:
    """去掉选项标签前缀。"""
    patterns = [
        rf"^[（(]\s*{re.escape(label)}\s*[）)]\s*",
        rf"^{re.escape(label)}\s*[.、．]\s*",
    ]
    for pattern in patterns:
        text = re.sub(pattern, "", text)
    return text.strip()

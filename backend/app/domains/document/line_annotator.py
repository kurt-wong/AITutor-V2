"""
LLM 行号标注器 — L1Document → L2DocumentAnnotation。

LLM 只输出行号引用、元数据和客观题短答案，不输出题干/选项/详解/解题过程原文。
Prompt 要求：question_number, question_type, section_id,
stem_line_ids, options_line_ids, answer_line_ids, explanation_line_ids,
difficulty, score, knowledge_points。
simple pipeline 直接使用 answer_line_ids / explanation_line_ids 从 L1 原文切片，
answer_matcher 仅作为缺失项 fallback。

详见 Docs/01_Product/T3_IMPLEMENTATION.md §8 Task 1.2。
遵守 V1_LESSONS 3.1/3.16（不输出 LaTeX 题干/选项/答案/解析原文）。
"""

from __future__ import annotations

import json
import logging
import re

from app.ai.gateway import LLMGateway
from app.ai.json_utils import parse_json_object
from app.domains.document.schemas_l1 import L1Document
from app.domains.document.schemas_l2 import L2DocumentAnnotation, L2QuestionAnnotation, L2SubQuestion

logger = logging.getLogger(__name__)

# Phase 2C：Annotation 版本标记（prompt 版本号，用于 llm_annotated_markdown 数据可比性）
ANNOTATION_PROMPT_VERSION = "v2.1-structure-v1"

# 小问标记：（1）（2）或 ①②③ 的括号格式（用于实验题/多小问题型归一化）
_SUB_QUESTION_RE = re.compile(r"[（(]\s*[一二三四五六七八九十\d]{1,2}\s*[）)]")

# 占位题号行（如 "（1）（集团校自创题）"）：不是完整题目，
# 不应被当作一道题，也不应把下一题题干绑进自己。
_PLACEHOLDER_QUESTION_RE = re.compile(
    r"^\s*[（(]\s*\d{1,3}\s*[）)]\s*[（(]集团(?:校)?自创题[）)]\s*$"
)
_WORDBANK_SECTION_RE = re.compile(r"选词填空|词汇填空|vocabulary|word_fill")
_SECTION_HEADER_RE = re.compile(
    r"^(?:第[一二三四五六七八九十]+[节部分]|Part\s+\w+|Section\s+\w+)",
    re.IGNORECASE,
)
_QUESTION_NUMBER_RE = re.compile(
    r"^\s*(?:[（(]\s*(\d{1,3})\s*[）)]|(\d{1,3})\s*[.、．])\s*"
)

# 子题号：15(1) / 15（1）/ 16.1 等形式，归一化时只保留母题号。
_SUBPART_QUESTION_NUMBER_RE = re.compile(
    r"(\d{1,3})\s*(?:[（(]\s*(\d{1,3}|[一二三四五六七八九十]+)\s*[）)]|[.．]\s*(\d{1,3}))"
)

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
    "essay": "short_answer",  # writing/essay: subjective internally
    "writing": "short_answer",
    "composition": "short_answer",
    "作文": "short_answer",
    "写作": "short_answer",
    "写作题": "short_answer",
    "书面表达": "short_answer",
    "书面表达题": "short_answer",
}


def _canonical_question_type(qt: str) -> str:
    """将 LLM 题型变量归一化为 canonical 枚举。"""
    return _QUESTION_TYPE_CANONICAL.get(qt, qt)


def _count_sub_question_markers(text: str) -> int:
    """统计题干中的小问标记数量（（1）（2）...）。"""
    return len(_SUB_QUESTION_RE.findall(text or ""))


def _collect_stem_text(line_ids: list[str], doc: L1Document) -> str:
    """把 stem 行号收集为文本（用于题型归一化判断）。"""
    line_by_id = {l.line_id: l for l in doc.lines}
    return " ".join(
        line_by_id.get(lid).text for lid in line_ids if lid in line_by_id
    )


def _parse_parent_question_number(question_number: str) -> tuple[str, str] | None:
    """解析 "15(1)" / "15（1）" 等子题号。

    Returns:
        (母题号, 子题号)；不是子题号时返回 None。
    """
    m = _SUBPART_QUESTION_NUMBER_RE.fullmatch((question_number or "").strip())
    if m and (m.group(2) or m.group(3)):
        return m.group(1), m.group(2) or m.group(3)
    return None


def _unique_ordered(items: list[str]) -> list[str]:
    """去重并保持首次出现顺序。"""
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _merge_subquestion_group(
    group: list[L2QuestionAnnotation],
    parent_number: str,
) -> L2QuestionAnnotation:
    """把同一母题下的子题标注合并为一道复合题。

    如果 LLM 同时给出母题和子题，也以子题标注为基准合并，避免重复题号。
    合并后的复合题统一作为 short_answer 处理，选项不再跨小问合并；小问内选项
    会保留在后续 stem 的确定性范围切片中。
    """
    stem_ids = _unique_ordered(
        lid for q in group for lid in q.stem_line_ids
    )
    shared_ids = _unique_ordered(
        lid for q in group for lid in q.shared_material_line_ids
    )
    knowledge_points = _unique_ordered(
        kp for q in group for kp in q.knowledge_points
    )
    answer_line_ids = _unique_ordered(
        lid for q in group for lid in q.answer_line_ids
    )
    explanation_line_ids = _unique_ordered(
        lid for q in group for lid in q.explanation_line_ids
    )
    section_id = None
    for q in group:
        if q.section_id:
            # "实验题_15"、"解答题_17" 合并后只保留大题型名，避免每个大题
            # 因独立 section_id 被误判为 section 不完整。
            section_id = re.sub(r"_\d+$", "", q.section_id)
            break

    scores = [q.score for q in group if q.score is not None]
    source_pages = [q.source_page for q in group if q.source_page is not None]
    structure_signature = next(
        (q.structure_signature for q in group if q.structure_signature),
        None,
    )
    return L2QuestionAnnotation(
        question_number=parent_number,
        question_type="short_answer",
        original_question_type=next(
            (q.original_question_type for q in group if q.original_question_type), None
        ),
        section_id=section_id,
        answer_structure=next((q.answer_structure for q in group if q.answer_structure), None),
        word_bank=next((q.word_bank for q in group if q.word_bank), None),
        shared_material_line_ids=shared_ids,
        stem_line_ids=stem_ids,
        options_line_ids={},
        answer=None,
        answer_line_ids=answer_line_ids,
        explanation_line_ids=explanation_line_ids,
        difficulty=next(
            (q.difficulty for q in group if q.difficulty is not None), None
        ),
        score=sum(scores) if scores else None,
        knowledge_points=knowledge_points,
        confidence=min(q.confidence for q in group) if group else 0.5,
        source_page=min(source_pages) if source_pages else None,
        structure_signature=structure_signature,
    )


def _normalize_subquestion_questions(
    questions: list[L2QuestionAnnotation],
) -> list[L2QuestionAnnotation]:
    """把子题号归一化为母题号，并稳定合并（33 题 -> 20 题）。

    复现性差异的根因是 LLM 有时把实验题/解答题小问各自标注为独立题目，
    有时又输出母题，导致 question_count 在 33 与 20 间不稳定。此处在
    anchor_corrector 之前统一子题，后续再按“起点 -> 下一题起点”做确定性
    stem 范围扩展。
    """
    groups: dict[str, list[L2QuestionAnnotation]] = {}
    has_subparts: dict[str, bool] = {}
    for q in questions:
        parsed = _parse_parent_question_number(q.question_number)
        key = parsed[0] if parsed else q.question_number
        groups.setdefault(key, []).append(q)
        has_subparts[key] = has_subparts.get(key, False) or parsed is not None

    emitted: set[str] = set()
    normalized: list[L2QuestionAnnotation] = []
    for q in questions:
        parsed = _parse_parent_question_number(q.question_number)
        key = parsed[0] if parsed else q.question_number
        if key in emitted:
            continue
        emitted.add(key)
        group = groups[key]
        if has_subparts.get(key):
            normalized.append(_merge_subquestion_group(group, key))
        else:
            normalized.extend(group)
    return normalized


def _is_placeholder_question_line(text: str) -> bool:
    """判断是否为仅含“集团校自创题”标记的占位题号行。"""
    return bool(_PLACEHOLDER_QUESTION_RE.match(text or ""))


def _drop_placeholder_questions(
    questions: list[L2QuestionAnnotation],
    doc: L1Document,
) -> list[L2QuestionAnnotation]:
    """移除被 LLM 误并入题干的占位题号行。

    真实文档中“（1）（集团校自创题）”不是题目，只是标记。若 LLM 把它和
    下一题题干合并为一道题，这里删除占位行，并把题号改回实际题干行号。
    """
    line_by_id = {l.line_id: l for l in doc.lines}
    result: list[L2QuestionAnnotation] = []
    for q in questions:
        stem_ids = []
        removed_placeholder = False
        for lid in q.stem_line_ids:
            line = line_by_id.get(lid)
            if line is not None and _is_placeholder_question_line(line.text):
                removed_placeholder = True
                continue
            stem_ids.append(lid)
        if not stem_ids and removed_placeholder:
            # 占位行被移除后没有真实题干。若答案表仍给出本题答案，说明这是
            # “集团校自创题”的真实题位，保留为待人工补题；否则视为伪占位题号丢弃。
            if q.answer or q.answer_line_ids:
                result.append(q)
                continue
            continue
        if not stem_ids:
            # 无效行号等场景保留题目，由 anchor_corrector 的确定性回退处理。
            result.append(q)
            continue
        q.stem_line_ids = stem_ids
        first_line = line_by_id.get(stem_ids[0])
        if removed_placeholder and first_line is not None:
            m = _QUESTION_NUMBER_RE.match(first_line.text)
            if m:
                actual_number = m.group(1) or m.group(2)
                if actual_number and actual_number != q.question_number:
                    q.question_number = actual_number
        result.append(q)
    return result


def _split_no_material_fill_composites(
    questions: list[L2QuestionAnnotation],
) -> list[L2QuestionAnnotation]:
    """Split fill-in composites that do not actually share material.

    A composite is defined by shared material.  If the LLM marks a fill-in
    question as composite but returns no ``shared_material_line_ids``, the
    sub-questions are treated as independent numbered blanks.  This prevents a
    hardcoded grammar-fill merge from removing Q12-Q20 from the document.
    """
    result: list[L2QuestionAnnotation] = []
    for question in questions:
        if (
            question.is_composite
            and question.question_type == "fill_in"
            and not question.shared_material_line_ids
        ):
            if not question.sub_questions:
                question.is_composite = False
                result.append(question)
                continue
            for index, sub in enumerate(question.sub_questions):
                qno = str(sub.qno or "").strip()
                if not qno:
                    continue
                answer_ids = (
                    question.answer_line_ids[index : index + 1]
                    if index < len(question.answer_line_ids)
                    else []
                )
                result.append(L2QuestionAnnotation(
                    question_number=qno,
                    question_type="fill_in",
                    original_question_type=question.original_question_type,
                    section_id=question.section_id,
                    answer_structure=question.answer_structure,
                    word_bank=question.word_bank,
                    shared_material_line_ids=[],
                    stem_line_ids=list(question.stem_line_ids),
                    options_line_ids={},
                    answer=sub.answer,
                    answer_line_ids=answer_ids,
                    explanation_line_ids=[],
                    difficulty=question.difficulty,
                    score=sub.score,
                    knowledge_points=list(sub.knowledge_points),
                    confidence=question.confidence,
                    source_page=question.source_page,
                    is_composite=False,
                    sub_questions=None,
                ))
            continue
        result.append(question)
    return result


def _find_shared_wordbank_line(
    doc: L1Document,
    first_question: L2QuestionAnnotation,
) -> str | None:
    """Find the word-bank line immediately before a word-fill question group."""
    line_by_id = {line.line_id: line for line in doc.lines}
    orders = [
        line_by_id[lid].order
        for lid in first_question.stem_line_ids
        if lid in line_by_id
    ]
    if not orders:
        return None
    first_order = min(orders)
    candidate: L1Line | None = None
    for line in doc.lines:
        if line.order >= first_order:
            break
        text = line.text.strip()
        if not text:
            continue
        if _QUESTION_NUMBER_RE.match(text) or _is_placeholder_question_line(text):
            continue
        if _SECTION_HEADER_RE.match(text):
            continue
        candidate = line
    return candidate.line_id if candidate is not None else None


def _is_wordbank_fill(question: L2QuestionAnnotation) -> bool:
    return (
        not question.is_composite
        and question.question_type == "fill_in"
        and bool(question.section_id)
        and bool(_WORDBANK_SECTION_RE.search(question.section_id))
    )


def _attach_word_bank_to_question(
    question: L2QuestionAnnotation,
    doc: L1Document,
) -> L2QuestionAnnotation:
    """Attach a shared word-bank line to a single word-fill question."""
    shared_id = _find_shared_wordbank_line(doc, question)
    if not shared_id:
        return question
    line_by_id = {line.line_id: line for line in doc.lines}
    if not question.word_bank and shared_id in line_by_id:
        question.word_bank = _parse_word_bank_line(line_by_id[shared_id].text)
    if shared_id not in (question.shared_material_line_ids or []):
        question.shared_material_line_ids = [shared_id] + list(question.shared_material_line_ids or [])
    if shared_id not in (question.stem_line_ids or []):
        question.stem_line_ids = [shared_id] + list(question.stem_line_ids or [])
    return question


def _parse_word_bank_line(text: str) -> list[str]:
    """Parse a word-bank line into a stable list of words/phrases."""
    raw = (text or "").strip()
    if not raw:
        return []
    if re.search(r"[;;；，,]", raw):
        parts = re.split(r"[;;；，,]+", raw)
    else:
        parts = raw.split()
    return [p.strip().strip(".;;；，,()（）") for p in parts if p.strip()]


def _normalize_word_bank(value) -> list[str] | None:
    """Normalize LLM word_bank output (list or string) for L2 metadata."""
    if isinstance(value, list):
        cleaned = [str(v).strip() for v in value if str(v).strip()]
        return cleaned or None
    if isinstance(value, str):
        return _parse_word_bank_line(value) or None
    return None


def _build_wordbank_composite(
    group: list[L2QuestionAnnotation],
    doc: L1Document,
) -> L2QuestionAnnotation:
    first = group[0]
    shared_id = _find_shared_wordbank_line(doc, first)
    line_by_id = {line.line_id: line for line in doc.lines}
    word_bank = list(first.word_bank or [])
    if not word_bank and shared_id and shared_id in line_by_id:
        word_bank = _parse_word_bank_line(line_by_id[shared_id].text)
    stem_ids: list[str] = []
    if shared_id:
        stem_ids.append(shared_id)
    for question in group:
        stem_ids.extend(question.stem_line_ids)

    sub_questions: list[L2SubQuestion] = []
    answers: list[str] = []
    answer_ids: list[str] = []
    explanation_ids: list[str] = []
    knowledge_points: list[str] = []
    scores: list[float] = []
    structure_signature = next(
        (question.structure_signature for question in group if question.structure_signature),
        None,
    )
    for question in group:
        sub_questions.append(L2SubQuestion(
            qno=question.question_number,
            question_type=question.question_type,
            answer=question.answer,
            knowledge_points=question.knowledge_points,
            score=question.score,
        ))
        if question.answer:
            answers.append(f"({question.question_number}) {question.answer}")
        answer_ids.extend(question.answer_line_ids)
        explanation_ids.extend(question.explanation_line_ids)
        knowledge_points.extend(question.knowledge_points)
        if question.score is not None:
            scores.append(question.score)

    return L2QuestionAnnotation(
        question_number=first.question_number,
        question_type="fill_in",
        original_question_type=first.original_question_type,
        section_id=first.section_id,
        answer_structure=first.answer_structure,
        word_bank=word_bank,
        shared_material_line_ids=[shared_id] if shared_id else list(first.stem_line_ids),
        stem_line_ids=_unique_ordered(stem_ids),
        options_line_ids={},
        answer=" ".join(answers) or None,
        answer_line_ids=_unique_ordered(answer_ids),
        explanation_line_ids=_unique_ordered(explanation_ids),
        difficulty=first.difficulty,
        score=sum(scores) if scores else None,
        knowledge_points=_unique_ordered(knowledge_points),
        confidence=min(q.confidence for q in group) if group else 0.5,
        source_page=first.source_page,
        structure_signature=structure_signature,
        is_composite=True,
        sub_questions=sub_questions,
    )


def _merge_wordbank_fill_composites(
    questions: list[L2QuestionAnnotation],
    doc: L1Document,
) -> list[L2QuestionAnnotation]:
    """Merge consecutive word-fill questions that share one word bank."""
    result: list[L2QuestionAnnotation] = []
    index = 0
    while index < len(questions):
        question = questions[index]
        if not _is_wordbank_fill(question):
            result.append(question)
            index += 1
            continue
        group: list[L2QuestionAnnotation] = []
        while (
            index < len(questions)
            and _is_wordbank_fill(questions[index])
            and questions[index].section_id == question.section_id
        ):
            group.append(questions[index])
            index += 1
        if len(group) >= 2:
            result.append(_build_wordbank_composite(group, doc))
        else:
            result.append(_attach_word_bank_to_question(group[0], doc))
    return result


logger = logging.getLogger(__name__)

# 标注 Prompt 模板
ANNOTATION_PROMPT = """你是一个试卷文档标注助手。给定一份试卷的文本行（带行号），请识别所有题目并输出标注结果。

## 规则
1. 每个题目必须包含：question_number, question_type, section_id, stem_line_ids, options_line_ids, answer_line_ids, explanation_line_ids；question_type 使用 canonical 枚举：single_choice / multiple_choice / fill_in / true_false / short_answer；英语写作/书面表达必须输出 essay（内部按 short_answer 处理，但入库必须保留 essay 原始题型）
2. difficulty 为必填字段，取值 1-5 整数（1=基础，2=简单，3=中等，4=较难，5=困难），必须为每道题给出，禁止省略。判断依据：考查单一概念的直接套用=1~2；需两步以上推理或综合两个知识点=3；涉及多知识点综合、复杂计算或易错陷阱=4；压轴题、强综合、非常规思路=5。若确实无法判断，输出 3（中等），不得输出 null。
2b. 可选字段：score, knowledge_points, answer, word_bank, answer_structure
2c. answer_structure 可选，仅当答案存在多答案/范围/特殊标注格式时输出 JSON；例如 {{"accepted_answers": ["that", "which"]}}、{{"range": {{"min": "24.00", "max": "25.00"}}}}、{{"error_span": "...", "explanation": "..."}}
2a. 可选字段 structure_signature（仅数学/物理/化学；其余科目输出 null）：结构签名，用于后续题族分析。格式为 JSON 对象，包含：
    - object: 考查对象（如 "函数单调性"、"匀变速直线运动"、"化学平衡"）
    - task: 题目任务（如 "求值"、"判断单调性"、"计算反应速率"）
    - method: 主要解法（如 "导数法"、"图像法"、"守恒法"）
    - condition: 给定约束/条件（如 "f(x)=x²-2x+3"，从题干原文保留文本；无独立条件时输出 null）
    注意：structure_signature 是 Annotation（LLM 解释），不是事实，随 prompt 版本变化。无法可靠判断时输出 null，禁止编造。
3. options_line_ids 的 key 是选项标签（A/B/C/D），value 是该选项所在的行号列表
4. 填空题和解答题的 options_line_ids 为空对象 {{}}
5. 共享材料题（如完形填空、阅读理解）用 section_id 标识共享材料范围
6. 共享材料题必须输出 shared_material_line_ids，值为该 section 公共材料（如文章段落）实际 L1 行号；独立题输出 []
7. 行号必须是文档中实际存在的行号（格式如 P1L001、P2L012）
7a. stem_markers 是语义定界标记：start 必须是该题题干在文档中的真实开头子串，且必须包含题号和足够多的后续文本；end 必须是题干在文档中的真实结尾子串。标记必须从文档原样复制，禁止改写、补全或归一化；无法确定稳定结尾时 end 输出 null。
7b. stem 包含范围：题号行 + 题干正文 + 图注/图题说明。实验题 stem 包含实验装置描述和实验条件，到第一个小题问题前结束。❌ 不包含选项行（选择题）或解题过程。
7c. 图注/图题（如"滑轮细线小车打点计时器Q 纸带沙桶图1"）属于题干的一部分，应包含在 stem_line_ids 中。
8. answer_line_ids：只指向该题最终结果所在的实际 L1 行。
   - 选择题/填空题：指向答案表或题后答案行
   - 解答题：按小题指向每个小题的最终结果行
   - ❌ 禁止把推导、变换、证明、中间计算过程行放入 answer_line_ids；这些行属于 explanation_line_ids
   - 如果最终结果与推导位于同一行，可以保留该行，但不要输出纯解题过程行
   - 找不到答案输出 []
8a. 解答题"最终结果行"识别规则：
   - 包含最终数值答案（如 "=3"、"0.45"）或最终结论（如 "综上"、"所以"、"则"）
   - ❌ 不包含纯中间推导步骤（"由题意得"、"代入得"、"化简得"、"设"）
   - 如果一个行同时包含推导和最终结果，该行可放入 answer_line_ids
   - 多个小题（(1)(2)(3)）分别指向各自的最终结果行
   - 判断依据：该行是否可以直接作为答案呈现给学生，而不需要额外推导
9. explanation_line_ids：指向该题详解/解题过程所在的实际 L1 行。找不到详解输出 []
10. answer 仅用于 single_choice / multiple_choice / true_false，值为答案表或题后答案中该题的短答案（如 "C"、"AB"）；其他题型输出 null。不要输出题干、选项、详解或解题过程原文；answer 只能是从文档答案区逐字提取的短结果。answer_line_ids 只允许放最终结果行，不能因为 answer 为 null 就把解题过程行放入 answer_line_ids
11. 必须输出文档中的每一道题，不得跳过题号；若无法定位某题，也要输出该题并给出空行号

## 综合题识别（材料题必须合并）

对于共享同一段材料/文章/实验描述/题图/前提条件的若干子题，必须输出为一道综合题，不要拆成独立题目。

**第一优先规则（共享即合并，不依赖能否独立作答）：**
- **只要多道题共享同一份材料/文章/题图/图表/前提条件，就合并为一道综合题**——无论每道子题是否有自己的选项、无论去掉材料后子题"看起来"能否作答。因为脱离共享材料/题图，子题就失去作答所需的上下文，不能作为真正独立的题目。
- 共享材料/题图的信号（任一项即判定共享）：
  - 卷面显式标识："读图/读表/读材料…完成 N—M 题"、"结合材料回答 N—M 题"
  - 题干均引用同一图表："如图""下图""读图""读表""下图为…""如下图所示""如表所示"且指向同一张图/表
  - 多题共享同一段文字材料/文章/实验描述/前提条件（shared_material_line_ids 重叠）
- 共享题图示例：地理"读图，完成 18—20 题"的 18/19/20；生物共享某实验示意图的多题；物理共享电路图的多题——**均合并为一道综合题**

**第二规则（独立题判断，仅当完全无共享材料/题图时）：**
- 每道题引用**各自独立的图/材料**（如 Q21 引用自己的"甲城市机动车流量变化图"、Q22 引用自己的阅兵图）→ **保持独立题**
- 化学 20 道独立选择题（无共享材料、无共享题图）→ 独立题
- 英语独立带题号的语法句子（各自独立、无共享文章）→ 独立题

**⚠️ 特别提醒：选择题组共享题图时必须合并，不要因为"每道选择题有自己选项"就判为独立题。**
选择题组一旦共享题图/材料，该图/材料就是题目不可分割的组成部分——去掉它，子题无法理解题意，所以必须合并为综合题，子题作为 sub_questions 保留各自题干/选项/答案。

**综合题类型举例：**
- 英语：完形填空、共享文章下的语法填空/词汇填空、阅读理解、七选五、阅读表达
- 语文：材料阅读、文言文阅读、诗歌阅读、散文阅读、微写作
- 化学：工艺流程、实验综合
- 物理：综合实验题
- 生物：实验设计题
- 历史/政治/地理：材料分析题
- **地理/生物/物理等：共享题图/图表/前提的选择题组**——卷面常以"读图/读表…完成 N—M 题"标识，或题干均含"如图为…"且指向**同一**图表/示意图/折线图/统计表/前提条件（如"读图，完成 18—20 题"的 18/19/20 三道选择题）

**共享题图判断要点（语义判断，不要只看有没有"完成 N—M 题"字样）：**
- 多道题的题干都引用**同一张图/表/示意图/前提**（如"读图完成 18—20 题"、或题干都写"如图为甲城市…"且指同一图）→ 共享题图 → **合并为综合题**
- 每道题引用**各自独立的图**（如 Q21 引用自己的"甲城市机动车流量变化图"、Q22 引用自己的阅兵图）→ **保持独立题**
- "读图完成 N—M 题"只是常见标识之一，**没有该字样但语义上共享同一图表/前提的，同样要合并**；反之，即使相邻也不能仅因题号连续而合并
- 题图引用信号：题干中的"如图""下图""读图""读表""下图为…""如下图所示"等指向同一图表

**英语试卷分组注意（按语义判断，不按题号机械合并）：**
- 多个小题只有在共享同一篇材料/文章/短文时才合并为综合题
- 独立带题号的句子，去掉材料后仍能独立作答，必须保持独立题
- 语法填空如果是一组独立句子，则每个句子是独立题；如果按 A/B/C 共享材料组织，则每篇材料合并为 1 道综合题
- 选词填空/词汇填空：如果多个带题号句子共享同一个词库，词库就是共享材料，合并为 1 道综合题；没有共享词库则保持独立
- 阅读理解按每篇文章合并，七选五按整篇材料合并，阅读表达按整篇材料合并
- ❌ 不得仅因为题型相同或题号连续就合并

**综合题输出格式：**
- question_number = 该组第一道题的大题号（如 "11"）
- question_type = 保留原始题型（cloze / reading / grammar_fill / seven_to_five / essay / single_choice / ...）
- is_composite = true
- stem_markers = 材料全文的首尾标记
- stem_line_ids = 只包含子题题干行号（❌ 不包含共享材料行；材料行只放 shared_material_line_ids）
- shared_material_line_ids = 材料全文的行号（含题图引用说明行；材料不得重复写入每道题的 stem_line_ids）
- answer = 所有子题答案（格式："(1) B (2) C (3) A ..."；选择题组如 "(18) D (19) B (20) C"）
- sub_questions = 子题元数据数组，每项包含：
  - qno: 子题编号（如 "1"、"2"、"（1）"、"18"）
  - question_type: 子题题型（fill_in / single_choice / ...）
  - stem_line_ids: 子题题干行号（选择题组为各题题干行）
  - options_line_ids: 子题选项行号（仅选择题子题，如 {{"A": [...], "B": [...], "C": [...], "D": [...]}}）
  - answer: 子题答案
  - knowledge_points: 知识点（可选）
  - score: 分值（可选）
  - sub_sub_questions: 可选，子题下的更深层子问（如 ⅠⅡⅢⅣ / ①②③④），结构同 sub_questions，可递归。

**⚠️ 子题 stem_line_ids 必须给出（2026-08-27 P4E.1 强化）**：
- **完形填空/语法填空/词汇填空等填空类子题**：子题"题干"就是材料中该题号对应的
  句子（含空位/下划线）。每个子题的 stem_line_ids 必须指向**含该题号/空位的那一行**
  （若题号与句子同行，给整行；若空位行与题号行不同，给空位所在行）。
  禁止输出空数组——否则子题在前端无法与选项/填空内容匹配。
- 选择题组子题（读图完成 18-20 题）：stem_line_ids 指向各题题干行。
- 若某子题确实找不到独立题干行（如空位嵌在长材料行中），也要给出含空位的
  材料行号（可与其他子题重叠该行）。

## 输出格式
严格输出 JSON 对象，不要输出其他内容：
```json
{{
  "filename": "文档文件名",
  "subject": "科目",
  "questions": [
    {{
      "question_number": "1",
      "question_type": "single_choice",
      "section_id": "阅读理解_1",
      "stem_markers": {{
        "start": "1. 已知函数f(x)=2x+1",
        "end": "则f(3)="
      }},
      "stem_line_ids": ["P1L004"],
      "options_line_ids": {{
        "A": ["P1L005"],
        "B": ["P1L006"],
        "C": ["P1L007"],
        "D": ["P1L008"]
      }},
      "answer": "C",
      "answer_line_ids": ["P5L003"],
      "explanation_line_ids": ["P6L001", "P6L002"],
      "shared_material_line_ids": ["P1L001", "P1L002", "P1L003"],
      "difficulty": 2,
      "score": 5.0,
      "knowledge_points": ["函数"],
      "structure_signature": {{
        "object": "函数单调性",
        "task": "判断单调性",
        "method": "导数法",
        "condition": "f(x)=x²-2x+3"
      }}
    }},
    {{
      "question_number": "11",
      "question_type": "fill_in",
      "section_id": "语法填空_A",
      "is_composite": true,
      "stem_markers": {{
        "start": "A. Global Gateway Camp",
        "end": "rebuild for a brighter future."
      }},
      "stem_line_ids": ["P2L001", "P2L002", "...", "P2L020"],
      "shared_material_line_ids": ["P2L001", "P2L002", "P2L003", "P2L004", "P2L005"],
      "answer": "(1) racing (2) dancing (3) built",
      "answer_line_ids": ["P9L010"],
      "sub_questions": [
        {{"qno": "11", "question_type": "fill_in", "answer": "racing", "knowledge_points": ["动词时态"]}},
        {{"qno": "12", "question_type": "fill_in", "answer": "dancing", "knowledge_points": ["非谓语动词"]}},
        {{"qno": "13", "question_type": "fill_in", "answer": "built", "knowledge_points": ["被动语态"]}}
      ],
      "difficulty": 3,
      "knowledge_points": ["语法填空"]
    }},
    {{
      "question_number": "18",
      "question_type": "single_choice",
      "is_composite": true,
      "section_id": "选择题_共享题图",
      "stem_markers": {{
        "start": "读图，完成18—20题",
        "end": "三种地貌类型依次分别是"
      }},
      "stem_line_ids": [],
      "shared_material_line_ids": ["P3L001", "P3L002", "P3L003", "P3L004"],
      "options_line_ids": {{}},
      "answer": "(18) D (19) B (20) C",
      "answer_line_ids": ["P9L010"],
      "sub_questions": [
        {{
          "qno": "18", "question_type": "single_choice",
          "stem_line_ids": ["P3L005"],
          "options_line_ids": {{"A": ["P3L006"], "B": ["P3L007"], "C": ["P3L008"], "D": ["P3L009"]}},
          "answer": "D"
        }},
        {{
          "qno": "19", "question_type": "single_choice",
          "stem_line_ids": ["P3L010"],
          "options_line_ids": {{"A": ["P3L011"], "B": ["P3L012"], "C": ["P3L013"], "D": ["P3L014"]}},
          "answer": "B"
        }},
        {{
          "qno": "20", "question_type": "single_choice",
          "stem_line_ids": ["P3L015"],
          "options_line_ids": {{"A": ["P3L016"], "B": ["P3L017"], "C": ["P3L018"], "D": ["P3L019"]}},
          "answer": "C"
        }}
      ],
      "difficulty": 3,
      "knowledge_points": ["地貌"]
    }},
    {{
      "question_number": "19",
      "question_type": "short_answer",
      "stem_markers": {{
        "start": "19. 已知函数$f(x)=\\sin(\\omega x+\\varphi)$",
        "end": "求实数m的取值范围。"
      }},
      "stem_line_ids": ["P3L008", "P3L009", "P3L010", "P3L011", "P3L012", "P3L013", "P3L014", "P3L015"],
      "answer_line_ids": ["P6L008", "P6L011", "P6L017", "P7L001", "P7L005"],
      "explanation_line_ids": ["P6L005", "P6L006", "P6L007", "P6L008", "P6L009", "P6L010", "P6L011", "P6L012", "P6L013", "P6L014", "P6L015", "P6L016", "P6L017", "P7L001", "P7L002", "P7L003", "P7L004", "P7L005"],
      "difficulty": 4,
      "score": 14.0,
      "knowledge_points": ["三角函数", "取值范围"]
    }}
  ],
  "metadata_confidence": 0.8,
  "warnings": []
}}
```

## 文档内容
文件名: {filename}

{text_lines}
"""


def build_annotation_prompt(
    doc: L1Document,
    retry_hints: list[str] | None = None,
) -> str:
    """构建标注 Prompt。

    将 L1 文档的行文本格式化为带行号的列表，发送给 LLM。
    """
    text_lines = []
    for line in doc.lines:
        text_lines.append(f"[{line.line_id}] {line.text}")

    prompt = ANNOTATION_PROMPT.format(
        filename=doc.filename,
        text_lines="\n".join(text_lines),
    )
    if retry_hints:
        hint_text = "\n".join(f"- {hint}" for hint in retry_hints)
        prompt += (
            "\n\n## 上一轮标注问题（必须修正）\n"
            "以下题目在上轮标注中未通过校验。请只修正这些问题对应的行号或字段，"
            "不要遗漏，也不要虚构不存在的行号。\n"
            f"{hint_text}\n"
        )
    return prompt


async def annotate_document(
    doc: L1Document,
    gateway: LLMGateway,
    *,
    temperature: float = 0.2,
    retry_hints: list[str] | None = None,
) -> L2DocumentAnnotation:
    """用 LLM 标注文档中的题目。

    Args:
        doc: L1 文档
        gateway: LLM 网关
        temperature: 生成温度

    Returns:
        L2DocumentAnnotation：标注结果
    """
    prompt = build_annotation_prompt(doc, retry_hints=retry_hints)

    # 调用 LLM
    response_text = await gateway.complete(prompt, temperature=temperature)

    # 解析 JSON
    parsed = parse_json_object(response_text)

    # 构建 L2DocumentAnnotation
    questions: list[L2QuestionAnnotation] = []
    valid_line_ids = {l.line_id for l in doc.lines}
    def _parse_subs(raw_subs: list | None) -> list[L2SubQuestion] | None:
        if not raw_subs:
            return None
        parsed_subs = []
        for sq_data in raw_subs:
            raw_sub_opts = sq_data.get("options_line_ids", {}) or {}
            sub_options = {
                label: _validate_line_ids(ids, valid_line_ids, "sub_options")
                for label, ids in raw_sub_opts.items()
            }
            nested_raw = sq_data.get("sub_sub_questions") or sq_data.get("sub_questions") or []
            parsed_subs.append(L2SubQuestion(
                qno=str(sq_data.get("qno", "")),
                question_type=sq_data.get("question_type"),
                stem_line_ids=_validate_line_ids(
                    sq_data.get("stem_line_ids", []), valid_line_ids, "sub_stem"
                ),
                options_line_ids=sub_options,
                answer=sq_data.get("answer"),
                knowledge_points=sq_data.get("knowledge_points", []),
                score=sq_data.get("score"),
                sub_sub_questions=_parse_subs(nested_raw),
            ))
        return parsed_subs


    for q_data in parsed.get("questions", []):
        # 验证行 ID 有效性
        markers = q_data.get("stem_markers")
        stem_start_marker = None
        stem_end_marker = None
        if isinstance(markers, dict):
            stem_start_marker = _clean_marker(markers.get("start"))
            stem_end_marker = _clean_marker(markers.get("end"))
        stem_ids = _validate_line_ids(
            q_data.get("stem_line_ids", []), valid_line_ids, "stem"
        )
        options_ids = {}
        for opt, lids in q_data.get("options_line_ids", {}).items():
            options_ids[opt] = _validate_line_ids(
                lids, valid_line_ids, f"option {opt}"
            )

        # C4: 提取并校验 shared_material_line_ids
        shared_material_ids = _validate_line_ids(
            q_data.get("shared_material_line_ids", []), valid_line_ids, "shared_material"
        )
        answer_ids = _validate_line_ids(
            q_data.get("answer_line_ids", []), valid_line_ids, "answer"
        )
        explanation_ids = _validate_line_ids(
            q_data.get("explanation_line_ids", []), valid_line_ids, "explanation"
        )
        raw_answer = q_data.get("answer")
        answer_text = (
            str(raw_answer).strip()
            if isinstance(raw_answer, str) and str(raw_answer).strip()
            else None
        )

        # 实验题/多小问题型归一化（WP5）：fill_in 但题干含多个小问标记（（1）（2）...）
        # → short_answer。物理实验题（"16． （1）...（2）...（3）..."）的 LLM 题型
        # 判定在 fill_in / short_answer 间不稳定，统一归 short_answer 使锚点扩展决策一致。
        original_question_type = str(q_data.get("question_type", "")).strip() or None
        raw_type = q_data.get("question_type", "unknown")
        raw_type = _canonical_question_type(raw_type)
        if raw_type == "fill_in":
            stem_text = _collect_stem_text(stem_ids, doc)
            if _count_sub_question_markers(stem_text) >= 2:
                raw_type = "short_answer"
                logger.info(
                    "question_type normalized fill_in->short_answer (multi sub-questions) q=%s",
                    q_data.get("question_number"),
                )

        # 解析综合题字段
        is_composite = q_data.get("is_composite", False)
        raw_sub_questions = q_data.get("sub_questions")
        sub_questions = _parse_subs(raw_sub_questions) if isinstance(raw_sub_questions, list) else None
        question = L2QuestionAnnotation(
            question_number=str(q_data.get("question_number", "")),
            question_type=raw_type,
            original_question_type=original_question_type,
            answer_structure=q_data.get("answer_structure") if isinstance(q_data.get("answer_structure"), dict) else None,
            word_bank=_normalize_word_bank(q_data.get("word_bank")),
            section_id=q_data.get("section_id"),
            stem_start_marker=stem_start_marker,
            stem_end_marker=stem_end_marker,
            shared_material_line_ids=shared_material_ids,
            stem_line_ids=stem_ids,
            options_line_ids=options_ids,
            answer=answer_text,
            answer_line_ids=answer_ids,
            explanation_line_ids=explanation_ids,
            difficulty=_normalize_difficulty(q_data.get("difficulty")),
            score=q_data.get("score"),
            knowledge_points=q_data.get("knowledge_points", []),
            confidence=q_data.get("confidence", 0.5),
            source_page=_get_source_page(stem_ids),
            is_composite=is_composite,
            sub_questions=sub_questions,
            # Phase 2C：Structure Signature（Annotation，非事实）
            structure_signature=_normalize_structure_signature(
                q_data.get("structure_signature")
            ),
        )
        questions.append(question)

    questions = _drop_placeholder_questions(questions, doc)
    questions = _split_no_material_fill_composites(questions)
    questions = _merge_wordbank_fill_composites(questions, doc)
    questions = _normalize_subquestion_questions(questions)

    return L2DocumentAnnotation(
        filename=doc.filename,
        subject=parsed.get("subject"),
        grade=parsed.get("grade"),
        year=parsed.get("year"),
        school=parsed.get("school"),
        questions=questions,
        metadata_confidence=parsed.get("metadata_confidence", 0.5),
        warnings=parsed.get("warnings", []),
        raw_response=response_text,
    )


def _clean_marker(value) -> str | None:
    """Normalize an optional semantic marker from LLM JSON."""
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def _normalize_structure_signature(value) -> dict | None:
    """Phase 2C：规范化 Structure Signature。

    保留 object/task/method/condition 四个字符串键；缺失或非 dict 返回 None（不编造）。
    """
    if not isinstance(value, dict):
        return None
    sig: dict = {}
    for key in ("object", "task", "method", "condition"):
        raw = value.get(key)
        if isinstance(raw, str) and raw.strip():
            sig[key] = raw.strip()
    return sig if sig else None


def _normalize_difficulty(value) -> int:
    """规范化难度：必须是 1-5 整数；缺失/非法默认 3（中等）。

    P0-3 修复（bugs.md BUG-012 §一 Q3）：
    - 此前 prompt 将 difficulty 标为可选、无校验透传 → 88% 题目 difficulty 为 NULL。
    - prompt 已改必填并给出判断依据；此处做代码层兜底：
      字符串数字（"3"）、浮点（3.0）归一为 int；越界/非法/缺失 → 3。
    """
    if isinstance(value, bool):
        return 3
    if isinstance(value, int):
        return value if 1 <= value <= 5 else 3
    if isinstance(value, float):
        iv = int(value)
        return iv if 1 <= iv <= 5 else 3
    if isinstance(value, str):
        s = value.strip()
        if s.isdigit():
            iv = int(s)
            return iv if 1 <= iv <= 5 else 3
    return 3


def _validate_line_ids(
    line_ids: list[str], valid_ids: set[str], field_name: str
) -> list[str]:
    """验证行 ID 有效性，过滤无效 ID。"""
    valid = []
    for lid in line_ids:
        if lid in valid_ids:
            valid.append(lid)
        else:
            logger.warning(
                "invalid_line_id field=%s line_id=%s", field_name, lid
            )
    return valid


def _get_source_page(line_ids: list[str]) -> int | None:
    """从行 ID 列表推断起始页码。"""
    if not line_ids:
        return None
    first_id = line_ids[0]
    # P1L001 → 1
    try:
        page_str = first_id.split("L")[0][1:]
        return int(page_str)
    except (IndexError, ValueError):
        return None

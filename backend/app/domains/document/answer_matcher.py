"""
答案与详解匹配器 — SlicedQuestion + L1 → 带 provenance 的 SlicedQuestion。

优先级（simple pipeline 传入 llm_annotation 时）：
0. LLM 语义提取的行号切片（llm_annotation）
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
from app.domains.document.schemas_l2 import (
    L2DocumentAnnotation,
    L2QuestionAnnotation,
    SOURCE_DOCUMENT_INLINE_EXPLANATION,
    SOURCE_LLM_ANNOTATION,
    SOURCE_DOCUMENT_SOLUTION_ANSWER,
    SlicedQuestion,
    SourceProvenance,
)

logger = logging.getLogger(__name__)

# 答案表题号标记：（1）A / (1) A（数学括号格式）或 1. D / 1、D / 1．D（英语点号格式）。
# 点号格式要求前后不是数字，避免把小数（3.2x）误判为题号。
_ANSWER_TABLE_MARKER_RE = re.compile(
    r"(?:[（(]\s*(\d{1,3})\s*[）)]|(?<![\d.、．])(\d{1,3})[.、．](?!\d))"
)
# 内联答案前缀（"11.【答案】would attend" 中【答案】后的才是答案文本）
_ANSWER_INLINE_PREFIX_RE = re.compile(r"^【答案】\s*")
# 答案表通常结束于“三、解答题”等长解答题区，避免把题号误当短答案。
_ANSWER_TABLE_STOP_RE = re.compile(
    r"^\s*[一二三四五六七八九十]+\s*[、．]?\s*解答题"
)
# 答案表遇到详解区标题（【导语】【详解】【解析】等）即停止，
# 避免详解/写作指导区中的 "1.词汇积累" 之类行覆盖真实答案。
# 注意：【答案】是答案区标题本身，不能作为停止标记。
_ANSWER_DETAIL_STOP_RE = re.compile(
    r"【(?:导语|详解|解析|分析)|【\d+\s*题详解】"
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
# 题干公式线索（用于检测“答案疑似公式符号丢失”）
_STEM_FORMULA_HINT_RE = re.compile(
    r"\\frac|\\sqrt|\\sum|\\int|sin|cos|tan|log|√|π|°"
)
# 可疑答案字符：PUA / 替换符 / 未解析 LaTeX
# answer_matcher 层使用严格正则：所有裸 \command（无 $ 包裹）都标记可疑
# 与 quality_gate 的宽松正则不同——answer_matcher 只降低置信度，不直接阻塞
_PUA_RE = re.compile(r"[\ue000-\uf8ff]")
_REPLACEMENT_RE = re.compile(r"\ufffd")
_LATEX_RESIDUE_RE = re.compile(r"\\[a-zA-Z]+")
_MATH_DOLLAR_RE = re.compile(r"\$[^$]*\$")


def _unpaired_latex(text: str) -> bool:
    """检测 $...$ 之外的裸 LaTeX 控制序列。

    成对 $ 包裹的公式是数学答案的合法形式（如 $\\frac{\\sqrt{2}}{2}$），
    不应判为"未解析 LaTeX"；裸 \\frac 等（无 $ 包裹）才是提取残留。
    """
    without_math = _MATH_DOLLAR_RE.sub("", text or "")
    return bool(_LATEX_RESIDUE_RE.search(without_math))


def _assess_answer_quality(answer_text: str, stem: str) -> tuple[float, list[str]]:
    """评估答案表来源的答案文本质量，返回 (confidence, 可疑原因列表)。

    原则（WP3）：document_answer_table 不再无条件 confidence=1.0。
    答案文本来自 PDF 文本层/OCR，公式可能以有损形式呈现（如
    \\frac{\\sqrt{2}}{2} 提取成 "2 2"），高置信度入库会污染题库。
    注：成对 $ 包裹的 LaTeX 公式是合法数学答案，不降级。
    """
    issues: list[str] = []
    conf = 0.95  # 来源可靠（教师版答案表），但文本可能受损

    if _PUA_RE.search(answer_text or ""):
        issues.append("答案含 PUA 字符，公式可能丢失")
        conf = 0.4
    if _REPLACEMENT_RE.search(answer_text or ""):
        issues.append("答案含替换符，公式可能丢失")
        conf = 0.4
    if _unpaired_latex(answer_text):
        issues.append("答案含未解析 LaTeX")
        conf = 0.4

    # 数学符号明显丢失：题干含公式线索，答案却只有短数字/符号碎片
    # （如 "2 2" 表示 \frac{\sqrt{2}}{2} 的文本层丢失）
    if _STEM_FORMULA_HINT_RE.search(stem or ""):
        stripped = re.sub(r"\s+", "", answer_text or "")
        # 单数字（如答案表明确写 "7"）不是公式丢失；只有多个符号碎片
        # 拼接出的短串（如 "2 2" 表示 \frac{\sqrt{2}}{2}）才降置信度。
        if stripped and len(stripped) >= 2 \
                and re.fullmatch(r"[0-9+\-*/^().,，。;；=<>≤≥∞π√]+", stripped) \
                and len(stripped) <= 4:
            issues.append("题干含公式但答案疑似符号丢失")
            conf = 0.4

    return conf, issues


def match_answers(
    sliced_questions: list[SlicedQuestion],
    doc: L1Document,
    *,
    llm_annotation: L2DocumentAnnotation | None = None,
) -> list[SlicedQuestion]:
    """为切片后的题目匹配答案和详解。

    Args:
        sliced_questions: 切片后的题目列表
        doc: L1 文档
        llm_annotation: 可选的 LLM 标注结果。simple pipeline 传入后，
            优先使用其中的 answer_line_ids / explanation_line_ids 从 L1 原文切片；
            缺失项仍走文档规则匹配/LLM 兜底。

    Returns:
        更新后的 SlicedQuestion 列表（带 provenance）
    """
    parsed_table = _parse_answer_table(doc)
    answer_table = {k: v[0] for k, v in parsed_table.items()}
    answer_table_sources = {k: v[1] for k, v in parsed_table.items()}
    explanation_map = _parse_explanations(doc)
    solution_blocks = _parse_solution_blocks(doc)
    if llm_annotation is not None:
        _apply_llm_annotation_answers(
            sliced_questions,
            llm_annotation,
            doc,
            solution_blocks=solution_blocks,
        )

    for sq in sliced_questions:
        # 选择题组综合题：父题答案 = 子题答案汇总（content_slicer 已生成），
        # 不走答案表匹配——文末答案表按子题号给单字母（如 18→B），会覆盖
        # merged_answer 为单个字母，丢失子题汇总。跳过单题匹配，保留汇总答案。
        if (
            getattr(sq, "is_composite", False)
            and sq.question_type in ("single_choice", "multiple_choice")
        ):
            continue
        _match_single_question(
            sq, doc, answer_table, answer_table_sources,
            explanation_map, solution_blocks,
        )

    logger.info(
        "answer_matching questions=%d matched=%d",
        len(sliced_questions),
        sum(1 for sq in sliced_questions if sq.answer is not None),
    )

    return sliced_questions


# 答案表表格格式（物理卷）："题号  1  2  3..." 行 + "答案  C  B  D..." 行配对
_TABLE_QNUM_RE = re.compile(r"^\s*题号\s+(.+)$")
_TABLE_ANSWER_RE = re.compile(r"^\s*答案\s+(.+)$")
# PP-StructureV3 把物理答案表格识别为 HTML 表格行（<table><tr><td>题号</td>...）
_HTML_TABLE_RE = re.compile(r"<table>.*?</table>", re.DOTALL)
_TD_RE = re.compile(r"<td>(.*?)</td>")
_TR_RE = re.compile(r"<tr>(.*?)</tr>", re.DOTALL)
# 答案分值后缀清洗："B （2分）" → "B"
_SCORE_SUFFIX_RE = re.compile(r"（\d+\s*分）\s*$")

# 解答题解题过程：题号行（(17)(共13分) / 17.（7分）解：）
_SOLUTION_QUESTION_NUMBER_RE = re.compile(
    r"^\s*(?:[（(]\s*(\d{1,3})\s*[）)]|(\d{1,3})\s*[.、．])\s*"
)
_PAGE_FOOTER_RE = re.compile(r"^\s*第\s*\d+\s*页/共\s*\d+\s*页\s*$")
_SUB_ANSWER_MARKER_RE = re.compile(
    r"^\s*(?:[（(]\s*(?:[ⅠⅡⅢⅣ一二三四五六七八九十\d]{1,3})\s*[）)]|"
    r"①|②|③|④|⑤|⑥|⑦|⑧|⑨|⑩)\s*"
)
_SCORE_MARKER_RE = re.compile(r"\d+\s*分")
_RESULT_PHRASE_RE = re.compile(
    r"(?:解集是|定义域为|值域(?:是|为)|取值范围(?:是|为)|对称轴方程为|"
    r"答案是|结论是|最大值为|最小值为|取得最大值|取得最小值|"
    r"综上|因此|所以|故|解得|可得|可知|即)"
)
_SOLUTION_SCORE_SUFFIX_RE = re.compile(
    r"(?:\s*…+\s*\d+\s*分|\s*[（(]\s*\d+\s*分\s*[）)]|\s*\d+\s*分)\s*$"
)
_SHORT_MATH_CONTINUATION_RE = re.compile(r"^[\d.,，。+\-$]*$")

# LLM 答案行号切片中的明显非答案线索：解析/分析标题和题干特征词。
_NON_ANSWER_HEADER_RE = re.compile(
    r"^(?:【(?:分析|详解|解析|解答|导语)】|本题(?:主要)?考查|考点考查|能力考查|核心素养|"
    r"题目(?:要求|考查)|(?:以下|下列)(?:说法|关于|表述)|"
    r"\d+题(?:详解|解析|分析)|(?:参考)?答案[:：])"
)
_STEM_FEATURE_RE = re.compile(r"(?:下列|关于|如图|已知|本题|题目|求|设|若)")

# 选择题答案应匹配的模式：单字母 A-D 或组合 AB/ACD 等
_CHOICE_ANSWER_RE = re.compile(r"^[A-G]{1,7}$")

# 答案区标题行（如"54.【答案】例文"），不是真正的答案内容
_ANSWER_SECTION_TITLE_RE = re.compile(
    r"^\d+\.?\s*【答案】\s*例文\s*$"
)
# 图解/标签行（如"O \n37T \nF"），不是答案内容
_DIAGRAM_LABEL_RE = re.compile(
    r"^[A-Za-z0-9\s\n/\\]+$"
)


def _filter_answer_section_titles(
    answer_ids: list[str],
    line_by_id: dict,
) -> list[str]:
    """从 answer_line_ids 中移除答案区标题行（如"54.【答案】例文"）。"""
    return [
        lid for lid in answer_ids
        if lid in line_by_id
        and not _ANSWER_SECTION_TITLE_RE.match(line_by_id[lid].text or "")
    ]


def _filter_diagram_labels(
    answer_ids: list[str],
    line_by_id: dict,
) -> list[str]:
    """从 answer_line_ids 中移除纯图解/标签行（如"O \n37T \nF"）。

    判断规则：行内容只含字母、数字、空格、换行、斜杠，
    且不含中文、不含等号/不等号、不含 LaTeX 公式。
    """
    result = []
    for lid in answer_ids:
        line = line_by_id.get(lid)
        if not line:
            continue
        text = (line.text or "").strip()
        # 含中文 → 可能是答案
        if re.search(r"[\u4e00-\u9fff]", text):
            result.append(lid)
            continue
        # 含等号/不等号/LaTeX → 可能是答案
        if re.search(r"[=<>$\\]|\\[a-zA-Z]", text):
            result.append(lid)
            continue
        # 只含简单符号且长度短 → 可能是图解标签
        if _DIAGRAM_LABEL_RE.match(text) and len(text.replace("\n", "").replace(" ", "")) < 20:
            continue
        result.append(lid)
    return result


# 匹配题号行（如"18.（9分）解："、"19. (13分)"）
_QUESTION_HEADER_RE = re.compile(
    r"^\s*\d{1,3}\s*[.、．]\s*[（(]\s*\d+\s*分\s*[）)]"
)


def _filter_to_question_boundary(
    answer_ids: list[str],
    question_number: str,
    line_by_id: dict,
) -> list[str]:
    """将 answer_line_ids 限制在当前题目的解题范围内。

    范围 = 当前题号行之后到下一个题号行之前。
    超出范围的行（属于下一题）必须丢弃。
    """
    if not answer_ids:
        return answer_ids

    # 按文档顺序排列所有行
    all_lines = sorted(line_by_id.values(), key=lambda l: l.order)

    # 找当前题号行和下一题号行的位置
    current_q_start = None
    next_q_start = None
    found_current = False

    for line in all_lines:
        text = line.text or ""
        if _QUESTION_HEADER_RE.match(text):
            # 提取题号
            m = re.match(r"^\s*(\d{1,3})\s*[.、．]", text)
            if m:
                q_num = m.group(1)
                if q_num == question_number:
                    current_q_start = line.order
                    found_current = True
                elif found_current and next_q_start is None:
                    next_q_start = line.order
                    break

    if current_q_start is None:
        return answer_ids

    # 过滤：只保留在 [current_q_start, next_q_start) 范围内的行
    result = []
    for lid in answer_ids:
        line = line_by_id.get(lid)
        if not line:
            continue
        if line.order < current_q_start:
            continue
        if next_q_start is not None and line.order >= next_q_start:
            continue
        result.append(lid)
    return result


def _parse_html_answer_table(text: str) -> list[tuple[str, str]] | None:
    """解析 PP HTML 表格答案区，返回 [(题号, 答案), ...]。

    格式：<table><tr><td>题号</td><td>1</td>...</tr>
               <tr><td>答案</td><td>C</td>...</tr></table>
    非 HTML 表格或结构不完整返回 None。
    """
    table_match = _HTML_TABLE_RE.search(text)
    if not table_match:
        return None
    qnums: list[str] = []
    answers: list[str] = []
    for row in _TR_RE.findall(table_match.group(0)):
        tds = [t.strip() for t in _TD_RE.findall(row)]
        if not tds:
            continue
        if tds[0] == "题号":
            qnums = [t for t in tds[1:] if t.isdigit()]
        elif tds[0] == "答案" and qnums:
            answers = tds[1:]
    if qnums and answers:
        return list(zip(qnums, answers))
    return None


def _logical_segments(line: L1Line) -> list[tuple[str, str]]:
    """把一行 L1 文本按换行拆成逻辑片段，返回 [(text, line_id)]。"""
    result: list[tuple[str, str]] = []
    for segment in (line.text or "").splitlines():
        text = segment.strip()
        if text:
            result.append((text, line.line_id))
    return result


def _extract_solution_qnum(text: str) -> tuple[str | None, str]:
    """从解答题题号行提取题号和剩余文本。"""
    m = _SOLUTION_QUESTION_NUMBER_RE.match(text or "")
    if not m:
        return None, text or ""
    return m.group(1) or m.group(2), text[m.end():]


def _is_solution_question_header(text: str) -> bool:
    """判断是否为解答题题号行，而不是解题内容中的 (1)/（2）小问。"""
    q_num, rest = _extract_solution_qnum(text)
    if q_num is None:
        return False
    rest = rest.strip()
    if not rest:
        return True
    if rest.startswith("【答案】") or rest.startswith("【解析】"):
        return True
    # 允许 "（共13分）"、"（7分）"、"（7分）解：" 等题号行后缀。
    rest = re.sub(r"^[（(]?\s*(?:共\s*)?\d+\s*分[）)]?\s*", "", rest)
    rest = re.sub(r"^解\s*[：:]\s*", "", rest)
    return not rest.strip()


def _clean_solution_segment(text: str) -> str:
    """清理解题片段中的页脚和分值后缀。"""
    text = _PAGE_FOOTER_RE.sub("", text or "").strip()
    text = _SOLUTION_SCORE_SUFFIX_RE.sub("", text).strip()
    return text


def _is_answer_result_segment(text: str) -> bool:
    """判断解题片段是否包含可作答案的结果句。"""
    raw = _PAGE_FOOTER_RE.sub("", text or "").strip()
    if not raw:
        return False
    has_score = bool(_SCORE_MARKER_RE.search(raw))
    clean = _SOLUTION_SCORE_SUFFIX_RE.sub("", raw).strip()
    if not clean:
        return False
    # “（Ⅲ）不存在，理由如下：”只是证明小标题，不是最终答案；
    # 若双源仲裁选择 PP 的“（）不存在”而另一轮选择 native 的“（Ⅲ）不存在”，
    # 会直接造成复现性差异，因此统一不作为答案候选。
    if "理由如下" in clean or "证明如下" in clean:
        return False
    starts_sub = bool(_SUB_ANSWER_MARKER_RE.match(clean))
    is_result_phrase = bool(_RESULT_PHRASE_RE.search(clean))
    if starts_sub and (has_score or len(clean) <= 30):
        return True
    if has_score and (
        is_result_phrase
        or any(marker in clean for marker in ("=", "∈", "是", "为", "增大", "减小"))
    ):
        return True
    return False


def _extract_answer_from_solution(
    segments: list[tuple[str, str]],
) -> tuple[str | None, list[str]]:
    """从解答题解题片段提取答案候选行，返回 (answer_text, answer_line_ids)。"""
    candidates: list[str] = []
    line_ids: list[str] = []
    seen_line_ids: set[str] = set()

    def add_candidate(text: str, line_id: str) -> None:
        if text in candidates:
            return
        candidates.append(text)
        if line_id not in seen_line_ids:
            line_ids.append(line_id)
            seen_line_ids.add(line_id)

    for index, (text, line_id) in enumerate(segments):
        if not _is_answer_result_segment(text):
            continue
        clean = _clean_solution_segment(text)
        if not clean:
            continue
        # 结果行前若有“所以/解得...=”或“2.”这类续行，也应并入答案。
        # 例如 tanθ=-2 被 PP 拆成两行，且结果行本身带分值标记。
        pending: list[tuple[str, str]] = []
        j = index - 1
        while j >= 0:
            prev_text, prev_line_id = segments[j]
            prev_clean = _clean_solution_segment(prev_text)
            if not prev_clean or prev_clean in candidates:
                break
            if _is_answer_result_segment(prev_text):
                break
            is_short_math = (
                len(prev_clean) <= 8
                and bool(_SHORT_MATH_CONTINUATION_RE.match(prev_clean))
            )
            is_formula_continuation = (
                _RESULT_PHRASE_RE.search(prev_clean)
                and bool(re.search(r"[=:：+\-]\s*$", prev_clean))
            )
            if not (is_short_math or is_formula_continuation):
                break
            pending.append((prev_clean, prev_line_id))
            j -= 1
        for prev_clean, prev_line_id in reversed(pending):
            add_candidate(prev_clean, prev_line_id)
        add_candidate(clean, line_id)
    if not candidates:
        return None, []
    return "；".join(candidates), line_ids


def _parse_solution_blocks(doc: L1Document) -> dict[str, dict]:
    """解析“解答题”区内的题后解题过程，返回 {题号: {segments, line_ids, text}}。

    用于数学/物理解答题：教师版没有独立短答案表，答案与详解都写在
    “三、解答题 / 四、解答题”之后的解题过程中。PP 一行内可能用换行把
    多道题/多个条件挤在一起，因此按换行片段解析，并在遇到下一题号时截断。
    """
    blocks: dict[str, dict] = {}
    current_q: str | None = None
    current_segments: list[tuple[str, str]] = []
    in_solution_section = False

    def flush() -> None:
        nonlocal current_q, current_segments
        if not current_q or not current_segments:
            current_q = None
            current_segments = []
            return
        line_ids: list[str] = []
        seen_ids: set[str] = set()
        text_parts: list[str] = []
        for text, line_id in current_segments:
            clean = _clean_solution_segment(text)
            if clean:
                text_parts.append(clean)
            if line_id not in seen_ids:
                line_ids.append(line_id)
                seen_ids.add(line_id)
        blocks[current_q] = {
            "segments": list(current_segments),
            "line_ids": line_ids,
            "text": "\n".join(text_parts),
        }
        current_q = None
        current_segments = []

    for line in doc.lines:
        if not in_solution_section:
            if _ANSWER_TABLE_STOP_RE.match(line.text) or _ANSWER_SECTION_RE.search(line.text):
                in_solution_section = True
            continue

        for text, line_id in _logical_segments(line):
            if _PAGE_FOOTER_RE.match(text):
                continue
            q_num, _ = _extract_solution_qnum(text)
            if _is_solution_question_header(text) and q_num:
                flush()
                current_q = q_num
                current_segments = []
                continue
            if current_q:
                current_segments.append((text, line_id))

    flush()
    return blocks


def _is_ocr_source(source: str) -> bool:
    """判断 L1 行来源是否为 OCR。"""
    return source in ("ppsv3", "paddleocr", "mimo", "deepseek_vl")


def _parse_answer_table(doc: L1Document) -> dict[str, tuple[str, str]]:
    """解析文末答案表，返回 {题号: (答案, 来源)}。

    来源取值：
    - "native"：来自 native L1 行（PyMuPDF 文本层，可靠）
    - "ocr"：来自 OCR L1 行（PP-StructureV3/VL，可能识别错误）

    支持：
    - 逐行格式（数学 "（1）A" 括号 / 英语 "1. D" 点号）；
    - 多行格式（英语多个【答案】区块，详解区之间穿插）；
    - 表格格式（物理 "题号 1 2 3" + "答案 C B D" 两行配对）。

    遇详解标题（【导语】等）暂停收集，遇下一个"参考答案"/【答案】标题恢复；
    解析区之后的写作指导行（如 "1.词汇积累"）因处于详解区块内而被跳过。
    """
    table: dict[str, tuple[str, str]] = {}
    in_answer_section = False
    in_detail_block = False
    pending_qnums: list[str] = []
    table_keys: set[str] = set()  # 表格格式已给出的题号（权威，后续行不得覆盖）

    def add_answer(q_num: str, answer: str, line_source: str) -> None:
        """写入答案并记录来源。native 优先（后写覆盖先写）。"""
        source = "native" if not _is_ocr_source(line_source) else "ocr"
        if q_num in table and table[q_num][1] == "native" and source == "ocr":
            return  # native 答案已存在，OCR 不覆盖
        table[q_num] = (answer, source)

    for line in doc.lines:
        if _ANSWER_SECTION_RE.search(line.text):
            in_answer_section = True
            in_detail_block = False
            continue

        if not in_answer_section:
            continue

        if _ANSWER_TABLE_STOP_RE.match(line.text):
            break

        if _ANSWER_DETAIL_STOP_RE.search(line.text):
            in_detail_block = True
            pending_qnums = []
            continue

        if in_detail_block:
            # 只有新的答案区标题（【答案】/参考答案）才能恢复收集
            if _INLINE_ANSWER_RE.search(line.text) or _ANSWER_SECTION_RE.search(line.text):
                in_detail_block = False
            else:
                continue

        # PP HTML 表格格式（物理/生物答案区被 PP 识别为 <table>，属 OCR 来源）
        html_pairs = _parse_html_answer_table(line.text)
        if html_pairs is not None:
            for q_num, answer in html_pairs:
                add_answer(q_num, answer, line.source or "ocr")
                table_keys.add(q_num)
            continue

        # 表格格式：题号行 → 等待下一行答案行
        qnum_match = _TABLE_QNUM_RE.match(line.text)
        if qnum_match:
            pending_qnums = [t for t in qnum_match.group(1).split() if t.isdigit()]
            continue
        if pending_qnums:
            ans_match = _TABLE_ANSWER_RE.match(line.text)
            if ans_match:
                answers = ans_match.group(1).split()
                for q_num, answer in zip(pending_qnums, answers):
                    add_answer(q_num, answer, line.source or "native")
                    table_keys.add(q_num)
            pending_qnums = []
            continue

        markers = list(_ANSWER_TABLE_MARKER_RE.finditer(line.text))
        # 行内混合"点号题号 + 括号子步骤"（实验题如 "15． （1）1.50 （2 分）..."）：
        # 点号题号的答案延伸到行尾；括号子步骤不是独立题号。
        # 行内"同行多题"（英语完形如 "1.D2.C3.A4..."）：点号题号答案到下一个点号题号前。
        has_dot_marker = any(m.group(2) is not None for m in markers)
        for index, marker in enumerate(markers):
            q_num = marker.group(1) or marker.group(2)
            if q_num in table_keys:
                # 表格格式已给出该题答案（如物理 Q1-14），实验题分步骤
                # "（1）1.50..." 等括号子步骤不得覆盖表格答案
                continue
            next_marker = markers[index + 1] if index + 1 < len(markers) else None
            if marker.group(2) is not None and next_marker is not None \
                    and next_marker.group(2) is not None:
                # 点号题号 + 下一个点号题号（同行多题）：答案到下一个点号题号前
                end = next_marker.start()
            elif marker.group(2) is not None:
                # 点号题号 + 括号子步骤/行尾（实验题）：答案取到行尾
                end = len(line.text)
            else:
                end = (
                    next_marker.start() if next_marker is not None
                    else len(line.text)
                )
            answer = line.text[marker.end():end].strip()
            # 清理内联前缀："11.【答案】would attend" → "would attend"
            answer = _ANSWER_INLINE_PREFIX_RE.sub("", answer).strip()
            # 清理分值后缀（仅短答案）："B （2分）" → "B"；
            # 多步骤长答案（"（1）1.50 （2 分） （2）不能"）保留完整
            if len(answer) <= 6:
                answer = _SCORE_SUFFIX_RE.sub("", answer).strip()
            if q_num and answer:
                add_answer(q_num, answer, line.source or "native")

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


def _slice_l1_lines(
    line_ids: list[str],
    line_by_id: dict[str, L1Line],
) -> str:
    """按行号列表从 L1 原文切片文本。"""
    parts: list[str] = []
    for lid in line_ids:
        line = line_by_id.get(lid)
        if line:
            parts.append(line.text)
    return "\n".join(parts)


def _normalize_answer_ocr_markers(text: str) -> str:
    """Normalize common OCR variants of full-width answer markers."""
    return (
        (text or "")
        .replace("\u0433\u0438", "\uff08")
        .replace("\u0413\u0438", "\uff08")
        .replace("\u0433\u0439", "\uff09")
        .replace("\u0413\u0439", "\uff09")
    )


def _extract_answer_segment_for_question(
    line_text: str,
    question_number: str,
) -> str | None:
    """Extract the current question segment from a multi-question answer line."""
    normalized = _normalize_answer_ocr_markers(line_text)
    markers = list(_ANSWER_TABLE_MARKER_RE.finditer(normalized or ""))
    if not markers:
        return None
    for index, marker in enumerate(markers):
        marker_q = marker.group(1) or marker.group(2)
        if marker_q != question_number:
            continue
        end = (
            markers[index + 1].start()
            if index + 1 < len(markers)
            else len(normalized)
        )
        return normalized[marker.end():end].strip()
    return None


def _line_has_answer_markers(line_text: str) -> bool:
    """判断一行是否包含答案表题号标记。"""
    normalized = _normalize_answer_ocr_markers(line_text)
    return bool(_ANSWER_TABLE_MARKER_RE.search(normalized or ""))


def _slice_llm_answer_lines(
    line_ids: list[str],
    question_number: str,
    line_by_id: dict[str, L1Line],
    *,
    skip_wrong_marker_lines: bool = False,
    is_short_answer: bool = False,
) -> str:
    """按当前题号切片 LLM 答案行；同行多题答案按题号边界切分。

    is_short_answer=True 时，不跳过含 (1)/(2)/(3) 的行，
    因为解答题的 (1)/(2)/(3) 是小问答案行，不是答案表标记。
    """
    parts: list[str] = []
    for lid in line_ids:
        line = line_by_id.get(lid)
        if line is None:
            continue
        segment = _extract_answer_segment_for_question(
            line.text, question_number
        )
        if segment is not None:
            parts.append(segment)
        elif not (
            skip_wrong_marker_lines
            and not is_short_answer
            and _line_has_answer_markers(line.text)
        ):
            parts.append(line.text)
    return "\n".join(parts)


def _clean_llm_sliced_answer(question_number: str, text: str) -> str:
    """清理 LLM 答案行号切片中的常见机械噪声。"""
    text = _PAGE_FOOTER_RE.sub("", text or "").strip()
    text = _ANSWER_INLINE_PREFIX_RE.sub("", text).strip()
    text = re.sub(
        r"^\s*(?:故选|答案为|答案是|故答案为|答案[：:]|选(?=\s*[A-D]))\s*",
        "",
        text,
    ).strip()
    if question_number:
        text = re.sub(
            rf"^[（(]\s*{re.escape(question_number)}\s*[）)]\s*",
            "",
            text,
        ).strip()
        text = re.sub(
            rf"^(?<![\d.、．]){re.escape(question_number)}[.、．](?!\d)\s*",
            "",
            text,
        ).strip()
    text = _SOLUTION_SCORE_SUFFIX_RE.sub("", text).strip()
    text = re.sub(r"[。.．!！?？]+$", "", text).strip()
    return text


def _is_suspicious_llm_answer_text(answer_text: str, stem: str) -> bool:
    """判断 LLM 答案行号切片是否明显不是答案，避免把题干/分析头当作答案。"""
    text = (answer_text or "").strip()
    if not text:
        return True
    if _NON_ANSWER_HEADER_RE.match(text):
        return True

    norm_text = re.sub(r"\s+", "", text)
    norm_stem = re.sub(r"\s+", "", stem or "")
    if len(norm_text) >= 5 and (
        norm_text in norm_stem or norm_stem in norm_text
    ):
        return True
    if len(text) > 200 and _STEM_FEATURE_RE.search(text):
        return True
    return False


def _apply_llm_annotation_answers(
    sliced_questions: list[SlicedQuestion],
    llm_annotation: L2DocumentAnnotation,
    doc: L1Document,
    solution_blocks: dict[str, dict] | None = None,
) -> None:
    """优先使用 LLM 语义提取的答案/详解行号切片，缺失项留给规则匹配。

    对 short_answer 题目，优先从解题过程块提取答案行（确定性），
    LLM 的 answer_line_ids 只作兜底。
    """
    line_by_id = {l.line_id: l for l in doc.lines}
    by_number: dict[str, L2QuestionAnnotation] = {}
    for q in llm_annotation.questions:
        by_number.setdefault(q.question_number, q)

    for sq in sliced_questions:
        # 选择题组综合题（共享题图/材料，如"读图完成 18-20 题"）：父题答案已在
        # content_slicer 合并时由子题答案汇总生成（merged_answer，格式
        # "(1) C (2) B ..."），不是单个字母。LLM 的 answer_line_ids 指向
        # 文末答案表行时，_CHOICE_ANSWER_RE 纯字母校验会把它清空 →
        # 父题 answer=None → quality_gate 误报"答案缺失"。这里直接跳过：
        # 保留 content_slicer 生成的汇总答案（子题答案在 sub_questions 里）。
        if (
            getattr(sq, "is_composite", False)
            and sq.question_type in ("single_choice", "multiple_choice")
        ):
            continue
        q = by_number.get(sq.question_number)
        if q is None:
            continue

        # V1_LESSONS: short_answer 优先从解题过程提取答案行（确定性）
        solution_answer_ids: list[str] = []
        if q.question_type == "short_answer" and solution_blocks:
            solution = solution_blocks.get(sq.question_number)
            if solution:
                _, solution_answer_ids = _extract_answer_from_solution(
                    solution["segments"]
                )

        if solution_answer_ids:
            # 解题过程有确定性答案行 → 直接用，忽略 LLM 的 answer_line_ids
            answer_ids = solution_answer_ids
        else:
            answer_ids = _filter_answer_section_titles(
                [lid for lid in q.answer_line_ids if lid in line_by_id],
                line_by_id,
            )
            answer_ids = _filter_diagram_labels(answer_ids, line_by_id)
            # 解答题限制在当前题目的解题范围内（避免混入下一题的行）。
            # 综合题（材料+多小问）跳过：LLM 的 answer_line_ids 可能指向
            # 文末答案区（如历史材料题题目在 P7-8、答案在 P20），超出
            # 当前题目范围是正常结构，按"下一题边界"截断会清空答案 →
            # answer=None → quality_gate 误报 answer_missing。
            if q.question_type == "short_answer" and not getattr(
                sq, "is_composite", False
            ):
                answer_ids = _filter_to_question_boundary(
                    answer_ids, sq.question_number, line_by_id
                )

        # 优先级：answer_line_ids 切片 > q.answer 原文 > 文档匹配
        # 当 answer_ids 有效时，无条件从 L1 切片，确保同锚点 = 同答案
        # 选择题特殊处理：如果 LLM 直接给了有效字母答案，直接用，不走切片。
        # 原因：多题可能共享同一 answer_line_id（如答案表行），切片会取错答案。
        answer_text = None
        is_choice = q.question_type in ("single_choice", "multiple_choice")
        llm_direct_answer = (q.answer or "").strip() if q.answer else None
        if is_choice and llm_direct_answer:
            normalized_llm = llm_direct_answer.strip().upper().replace(" ", "")
            if _CHOICE_ANSWER_RE.match(normalized_llm):
                answer_text = llm_direct_answer
        if not answer_text and answer_ids:
            answer_text = _clean_llm_sliced_answer(
                sq.question_number,
                _slice_llm_answer_lines(
                    answer_ids,
                    sq.question_number,
                    line_by_id,
                    skip_wrong_marker_lines=True,
                    is_short_answer=(q.question_type == "short_answer"),
                ),
            )
            if answer_text and _is_suspicious_llm_answer_text(
                answer_text, sq.stem
            ):
                # 主观题（short_answer）的答案本身就是长文本，不做可疑检查
                if q.question_type != "short_answer":
                    logger.warning(
                        "llm_answer_slice_suspicious q=%s line_ids=%s",
                        sq.question_number,
                        answer_ids[:5],
                    )
                    answer_text = None
        # V1_LESSONS 3.17: 选择题答案必须是字母（A/B/C/D 等）
        # 如果切片结果不像答案字母，清空以让答案表匹配覆盖
        if answer_text and q.question_type in ("single_choice", "multiple_choice"):
            normalized = answer_text.strip().upper().replace(" ", "")
            if not _CHOICE_ANSWER_RE.match(normalized):
                logger.info(
                    "choice_answer_not_letter q=%s text=%r, clearing for answer_table",
                    sq.question_number, answer_text[:50],
                )
                answer_text = None
        # answer_ids 为空或切片失败时，回退到 LLM 原文
        if not answer_text:
            answer_text = (q.answer or "").strip() if q.answer else None
            # V1_LESSONS 3.17: 选择题的 LLM 原文也必须是字母
            if answer_text and q.question_type in ("single_choice", "multiple_choice"):
                normalized = answer_text.strip().upper().replace(" ", "")
                if not _CHOICE_ANSWER_RE.match(normalized):
                    logger.info(
                        "choice_llm_answer_not_letter q=%s text=%r, clearing",
                        sq.question_number, answer_text[:50],
                    )
                    answer_text = None
        if answer_text:
            sq.answer = answer_text
            sq.answer_line_ids = answer_ids
            if answer_ids:
                sq.answer_provenance = SourceProvenance(
                    field="answer",
                    source=SOURCE_LLM_ANNOTATION,
                    confidence=0.9,
                    evidence=(
                        "LLM 语义提取答案行号切片"
                        f" [{', '.join(answer_ids[:5])}]"
                    ),
                )
            else:
                # LLM 给了短答案但行号全部无效：没有锚点就不能当作 LLM 标注答案，
                # 清除不可信答案并降级为 llm_fallback，让规则匹配器覆盖。
                sq.answer = None
                sq.answer_line_ids = []
                sq.answer_provenance = SourceProvenance(
                    field="answer",
                    source="llm_fallback",
                    confidence=0.5,
                    evidence="LLM 兜底答案（无有效答案行号）",
                )

        explanation_ids = [
            lid for lid in q.explanation_line_ids if lid in line_by_id
        ]
        if explanation_ids:
            explanation_text = _slice_l1_lines(
                explanation_ids, line_by_id
            ).strip()
            if explanation_text:
                sq.explanation = explanation_text
                sq.explanation_line_ids = explanation_ids
                sq.explanation_provenance = SourceProvenance(
                    field="explanation",
                    source=SOURCE_LLM_ANNOTATION,
                    confidence=0.9,
                    evidence=(
                        "LLM 语义提取详解行号切片 "
                        f"[{', '.join(explanation_ids[:5])}]"
                    ),
                )


def _match_single_question(
    sq: SlicedQuestion,
    doc: L1Document,
    answer_table: dict[str, str],
    answer_table_sources: dict[str, str],
    explanation_map: dict[str, list[str]],
    solution_blocks: dict[str, dict],
) -> None:
    """为单个题目匹配答案和详解。

    V1_LESSONS 3.17: 选择题答案优先从答案表提取，LLM 只做兜底。
    来源感知：OCR 答案表可能识别错误（如生物 Q6 识别成 'D' 实为 'C'），
    当 OCR 答案表与 LLM 有效字母答案冲突时，保留 LLM 答案。
    """
    has_llm_answer = (
        sq.answer_provenance is not None
        and sq.answer is not None
        and sq.answer_provenance.source == SOURCE_LLM_ANNOTATION
    )
    has_llm_explanation = (
        sq.explanation_provenance is not None
        and sq.explanation is not None
        and sq.explanation_provenance.source == SOURCE_LLM_ANNOTATION
    )

    # V1_LESSONS 3.17: 答案表有该题且答案像字母 → 优先用答案表，忽略 LLM
    # 来源感知例外：答案表来自 OCR 且与 LLM 有效字母答案冲突 → 保留 LLM
    # （OCR 可能识别错误，LLM 从原文语义提取的答案更可靠）
    table_answer = answer_table.get(sq.question_number)
    if table_answer and _CHOICE_ANSWER_RE.match(
        table_answer.strip().upper().replace(" ", "")
    ):
        table_source = answer_table_sources.get(sq.question_number, "native")
        llm_answer_valid = (
            has_llm_answer
            and sq.answer
            and _CHOICE_ANSWER_RE.match(sq.answer.strip().upper().replace(" ", ""))
        )
        ocr_conflicts_with_llm = (
            table_source == "ocr"
            and llm_answer_valid
            and sq.answer.strip().upper() != table_answer.strip().upper()
        )
        if ocr_conflicts_with_llm:
            # OCR 答案表与 LLM 冲突 → 保留 LLM（OCR 识别错误）
            logger.info(
                "llm_answer_kept_over_ocr_table q=%s llm=%r table=%r",
                sq.question_number, sq.answer, table_answer,
            )
        else:
            if has_llm_answer:
                logger.info(
                    "answer_table_overrides_llm q=%s table=%r llm=%r",
                    sq.question_number, table_answer, sq.answer,
                )
            _match_document_answer(sq, doc, answer_table, solution_blocks)
    elif not has_llm_answer:
        _match_document_answer(sq, doc, answer_table, solution_blocks)

    if not has_llm_explanation:
        _match_document_explanation(sq, doc, solution_blocks, explanation_map)


def _match_document_answer(
    sq: SlicedQuestion,
    doc: L1Document,
    answer_table: dict[str, str],
    solution_blocks: dict[str, dict],
) -> None:
    """从文档答案表/解题过程/题后答案匹配答案。"""
    q_num = sq.question_number

    # 1. 尝试从答案表匹配
    if q_num in answer_table:
        answer_text = answer_table[q_num]
        hit_lines = _find_answer_table_lines(doc, q_num)
        evidence_parts = [
            f"{h['line_id']}={h['text'][:40]}" for h in hit_lines
        ]
        evidence = f"文末答案表第{q_num}题" + (
            f" [{'; '.join(evidence_parts)}]" if evidence_parts else ""
        )
        conf, quality_issues = _assess_answer_quality(answer_text, sq.stem)
        sq.answer = answer_text
        sq.answer_provenance = SourceProvenance(
            field="answer",
            source="document_answer_table",
            confidence=conf,
            evidence=evidence,
        )
        sq.answer_line_ids = [h["line_id"] for h in hit_lines]
        if quality_issues:
            # 标记可疑答案，quality_gate 会据此禁止自动发布并降 confidence
            sq.issues = list(sq.issues or []) + [
                f"答案可疑（{'；'.join(quality_issues)}）"
            ]
    else:
        # 2. 从题后解题过程定位答案（数学/物理解答题没有独立答案表）
        solution = solution_blocks.get(q_num)
        if solution:
            answer_text, answer_ids = _extract_answer_from_solution(
                solution["segments"]
            )
            if answer_text:
                conf, quality_issues = _assess_answer_quality(
                    answer_text, sq.stem
                )
                sq.answer = answer_text
                sq.answer_provenance = SourceProvenance(
                    field="answer",
                    source=SOURCE_DOCUMENT_SOLUTION_ANSWER,
                    confidence=conf,
                    evidence=(
                        "解答题解题过程定位答案 "
                        f"[{', '.join(answer_ids[:5])}]"
                    ),
                )
                sq.answer_line_ids = answer_ids
                if quality_issues:
                    sq.issues = list(sq.issues or []) + [
                        f"答案可疑（{'；'.join(quality_issues)}）"
                    ]
            else:
                sq.answer_provenance = SourceProvenance(
                    field="answer",
                    source="llm_fallback",
                    confidence=0.5,
                    evidence="无文档答案，需 LLM 推理",
                )
        else:
            # 3. 尝试内联答案
            inline_answer = _find_inline_answer(doc, q_num)
            if inline_answer:
                sq.answer = inline_answer["text"]
                sq.answer_provenance = SourceProvenance(
                    field="answer",
                    source="document_inline_answer",
                    confidence=0.9,
                    evidence=f"题后【答案】标记（{inline_answer['line_id']}）",
                )
                sq.answer_line_ids = [inline_answer["line_id"]]
            else:
                # 4. LLM 兜底
                sq.answer_provenance = SourceProvenance(
                    field="answer",
                    source="llm_fallback",
                    confidence=0.5,
                    evidence="无文档答案，需 LLM 推理",
                )


def _match_document_explanation(
    sq: SlicedQuestion,
    doc: L1Document,
    solution_blocks: dict[str, dict],
    explanation_map: dict[str, list[str]],
) -> None:
    """从解题过程/题后详解标记匹配详解。"""
    q_num = sq.question_number

    # 匹配详解
    if q_num in solution_blocks:
        block = solution_blocks[q_num]
        sq.explanation_line_ids = block["line_ids"]
        sq.explanation = block["text"] or None
        sq.explanation_provenance = SourceProvenance(
            field="explanation",
            source=SOURCE_DOCUMENT_INLINE_EXPLANATION,
            confidence=0.9,
            evidence=(
                f"解答题解题过程（{', '.join(block['line_ids'][:5])}）"
            ),
        )
    elif q_num in explanation_map:
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


def _find_answer_table_lines(doc: L1Document, q_num: str) -> list[dict]:
    """找到答案表中对应题号的行，返回 [{"line_id": ..., "text": ...}]。"""
    result: list[dict] = []
    in_answer_section = False

    for line in doc.lines:
        if _ANSWER_SECTION_RE.search(line.text):
            in_answer_section = True
            continue
        if not in_answer_section:
            continue

        if _ANSWER_TABLE_MARKER_RE.search(line.text):
            pattern = (
                rf"(?:[（(]\s*{re.escape(q_num)}\s*[）)]"
                rf"|(?<![\d.、．]){re.escape(q_num)}[.、．](?!\d))"
            )
            if not re.search(pattern, line.text):
                continue
            result.append({"line_id": line.line_id, "text": line.text})

    return result


def _find_inline_answer(doc: L1Document, q_num: str) -> dict | None:
    """找到题后的内联答案。

    只从答案区标题（"参考答案"/【答案】）之后扫描：正文题目中也可能出现
    "11. I promised..." 这类与答案同格式的题号行，全文档扫描会误判答案区起点。
    """
    # 答案区起点：从"参考答案"或独立【答案】标题行之后扫描。
    # 正文题目中可能出现 "11. I promised..." 这类与答案同格式的题号行，
    # 全文档扫描会误判起点；但无答案区标题时（题后答案格式）保持全文档扫描。
    # 注意："【答案】A"（带内容）是答案行本身，不是标题。
    start_idx = 0
    for idx, line in enumerate(doc.lines):
        if _ANSWER_SECTION_RE.search(line.text):
            start_idx = idx + 1
            break
        m = _INLINE_ANSWER_RE.search(line.text)
        if m and not (m.group(1) or "").strip():
            start_idx = idx + 1
            break

    found_q = False
    for line in doc.lines[start_idx:]:
        # 匹配 (1) 或 1. 格式的题号
        m = re.match(rf"^[（(]\s*{re.escape(q_num)}\s*[）)]", line.text)
        if not m:
            m = re.match(rf"^\s*{re.escape(q_num)}\s*[.、．]", line.text)
        if m:
            found_q = True
            # 题号与【答案】同行情景："11.【答案】would attend"
            same_line = _INLINE_ANSWER_RE.search(line.text)
            if same_line:
                return {"text": same_line.group(1).strip(), "line_id": line.line_id}
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

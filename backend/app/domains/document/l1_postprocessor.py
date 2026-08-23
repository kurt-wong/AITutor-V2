"""
L1 后处理器 — L1 生成后的机械后处理。

不依赖 LLM，只做文本层面的机械操作：
1. 题号前强制换行
2. 单行 A./B./C./D. 行内切分
3. 小数/化学式误拆回避
4. 连续行号校验

详见 Docs/01_Product/T3_IMPLEMENTATION.md §2.4。
遵守 V1_LESSONS 3.21/3.23。
"""

from __future__ import annotations

import re

from app.domains.document.schemas_l1 import L1Document, L1Line


# ── 题号模式 ──────────────────────────────────────────────────────

# 匹配题号开头的模式（行首）
_QUESTION_NUMBER_PATTERN = re.compile(
    r"^(\s*)(\d{1,3})\s*[.、．]\s*"
)

# 匹配大题编号（如 "二、" "三、"）
_SECTION_HEADER_PATTERN = re.compile(
    r"^(\s*)([一二三四五六七八九十]+)\s*[、．]\s*"
)

# 匹配小数（用于误拆回避）
_DECIMAL_PATTERN = re.compile(r"\d\.\d")

# 匹配化学式中的点（如 Fe₂O₃·H₂O）
_CHEMICAL_DOT_PATTERN = re.compile(r"[A-Z][a-z]?\d*·[A-Z]")

# 匹配单行多选项（A.xxx B.xxx C.xxx D.xxx）或（A）xxx（B）xxx
_INLINE_OPTIONS_PATTERN = re.compile(
    r"([A-D])\s*[.、．]\s*"
)
# 匹配括号选项（如 （A）xxx（B）xxx 或 (A) xxx(B) xxx）
_PAREN_OPTIONS_PATTERN = re.compile(
    r"[（(]\s*([A-D])\s*[）)]\s*"
)

# 匹配括号题号（如 (1) （2））
_PAREN_QUESTION_PATTERN = re.compile(
    r"^(\s*)[（(]\s*(\d{1,3})\s*[）)]\s*"
)

# 行内括号题号（如 “k的最大值为（16）关于...”）。
# 只处理全角括号，避免把答案表 (1)A (2)B 等 ASCII 括号格式拆散。
_PAREN_QUESTION_INLINE_PATTERN = re.compile(
    r"（\s*(\d{1,3})\s*）"
)


# ── 页脚过滤 ──────────────────────────────────────────────────────

_PAGE_FOOTER_RE = re.compile(r"^\s*第\s*\d+\s*页/共\s*\d+\s*页\s*$")


def _filter_page_footers(lines: list[L1Line]) -> list[L1Line]:
    """过滤页脚行（"第x页/共y页"），避免被纳入 stem_line_ids。"""
    return [l for l in lines if not _PAGE_FOOTER_RE.match(l.text or "")]


# ── 主入口 ──────────────────────────────────────────────────────


def postprocess_l1(doc: L1Document) -> L1Document:
    """对 L1Document 执行全部后处理，返回新的 L1Document。

    处理流程：
    1. 题号前强制换行
    2. 单行选项行内切分
    3. 重编行号

    不可变契约（V1 LESSONS 3.1）：
    - 返回新对象，不修改原始文档
    - raw_lines 保留处理前的原始行
    - pages[].lines 同步更新为 canonical lines
    """
    # 保留原始行用于追溯
    raw_lines = list(doc.lines)

    # 收集所有行，按 order 排序
    all_lines = sorted(doc.lines, key=lambda l: l.order)

    # Step 1: 题号前强制换行
    expanded = _expand_question_number_lines(all_lines)

    # Step 2: 单行选项行内切分
    expanded = _expand_inline_option_lines(expanded)

    # Step 2.5: 过滤页脚行（"第x页/共y页"）
    expanded = _filter_page_footers(expanded)

    # Step 3: 重编行号
    result_lines = _renumber_lines(expanded, doc.source)

    # Step 4: 同步 pages 的行引用
    updated_pages = _sync_pages_lines(doc.pages, result_lines)

    # 重建 L1Document
    return L1Document(
        filename=doc.filename,
        pages=updated_pages,
        lines=result_lines,
        images=doc.images,
        source=doc.source,
        total_pages=doc.total_pages,
        text_coverage=doc.text_coverage,
        raw_lines=raw_lines,
    )


# ── Step 1: 题号前强制换行 ──────────────────────────────────────


def _expand_question_number_lines(lines: list[L1Line]) -> list[L1Line]:
    """在题号标记前插入换行，将挤在同一行的内容拆开。

    处理场景：'D. 既不充分也不必要条件5.已知...'
    期望结果：两行 — 'D. 既不充分也不必要条件' + '5. 已知...'

    遵守 V1_LESSONS 3.23：小数/化学式误拆回避。
    """
    result: list[L1Line] = []

    for line in lines:
        text = line.text

        # table block 是结构化整体，不能按单元格里的数字/选项标记拆行。
        if line.block_type == "table":
            result.append(line)
            continue

        # 找到行内所有题号位置
        splits = _find_inline_question_numbers(text)

        if not splits:
            result.append(line)
            continue

        # 按位置拆分行
        parts = _split_at_positions(text, splits)

        for i, part in enumerate(parts):
            part = part.strip()
            if not part:
                continue

            # 保持原始 block_type 和 bbox（第一部分保持原样，后续部分 bbox 为 None）
            new_line = L1Line(
                line_id="",  # 稍后重编
                page_no=line.page_no,
                line_no_in_page=0,  # 稍后重编
                order=0,  # 稍后重编
                text=part,
                block_type=line.block_type,
                bbox=line.bbox if i == 0 else None,
                source=line.source,
                continuation=line.continuation,
                raw_sources=dict(line.raw_sources) if line.raw_sources else {},
                selected_source=line.selected_source,
                evidence=line.evidence,
                confidence=line.confidence,
            )
            result.append(new_line)

    return result


def _find_inline_question_numbers(text: str) -> list[int]:
    """找到行内题号的起始位置（排除行首已经是题号的情况）。

    返回需要拆分的位置列表。
    """
    splits: list[int] = []

    for match in re.finditer(r"\d{1,3}\s*[.、．]\s*", text):
        pos = match.start()

        # 跳过行首
        if pos == 0:
            continue

        # 跳过小数（如 3.2x）
        if _is_decimal_context(text, pos):
            continue

        # 跳过化学式点
        if _is_chemical_context(text, pos):
            continue

        # 检查前一个字符是否是 ASCII 字母（选项延续，如 "x5."）
        # 注意：中文字符不算，因为中文题号前常有中文
        prev_char = text[pos - 1] if pos > 0 else ""
        if prev_char.isascii() and prev_char.isalpha():
            continue

        # 跳过数字内部的点（如 "2015." 中 "5." 被误判为题号）
        # 匹配位置前一位是数字 → 跳过
        if prev_char.isdigit():
            continue

        splits.append(pos)

    paren_matches = list(_PAREN_QUESTION_INLINE_PATTERN.finditer(text))
    # 多题号同行通常是答案表，如 （5）A（10）D，不按题号拆行。
    if len(paren_matches) > 1:
        paren_matches = []
    for match in paren_matches:
        pos = match.start()

        # 跳过行首
        if pos == 0:
            continue

        prev_char = text[pos - 1] if pos > 0 else ""
        # 只拆中文上下文或空格后的括号题号，避免把公式/ASCII 表达式误拆。
        if prev_char.isascii() and not prev_char.isspace():
            continue

        next_char = text[match.end()] if match.end() < len(text) else ""
        # 答案表条目通常后接 ASCII 字母/数字，不拆；题干后接中文/空白才拆。
        if next_char and next_char.isascii() and not next_char.isspace():
            continue

        splits.append(pos)

    splits = sorted(set(splits))
    return splits


def _is_decimal_context(text: str, pos: int) -> bool:
    """检查位置是否在小数上下文中。

    pos 是匹配数字的起始位置（如 "3.125" 中 '3' 的位置）。
    点号在 pos+1，小数部分从 pos+2 开始。

    两种情况：
    1. 点号后紧跟数字（pos+2 是数字）→ 是小数
    2. 匹配的数字前面紧邻数字（如 "=3.125" 中 '3' 前是 '='）
       → 如果数字前面是数字，说明是更大数字的一部分
    """
    # 情况 1：点号后紧跟数字（小数部分）
    # 点号在 pos+1，检查 pos+2 是否是数字
    if pos + 2 < len(text) and text[pos + 1] == "." and text[pos + 2].isdigit():
        return True

    # 情况 2：匹配的数字前面紧邻数字
    num_start = pos
    while num_start > 0 and text[num_start - 1].isdigit():
        num_start -= 1
    # num_start 现在指向数字序列的起始位置
    # 检查这个位置前面是否还有数字（说明是更大数字的一部分）
    if num_start > 0 and text[num_start - 1].isdigit():
        return True

    return False


def _is_chemical_context(text: str, pos: int) -> bool:
    """检查位置是否在化学式上下文中。"""
    start = max(0, pos - 5)
    end = min(len(text), pos + 5)
    snippet = text[start:end]
    return bool(_CHEMICAL_DOT_PATTERN.search(snippet))


def _split_at_positions(text: str, positions: list[int]) -> list[str]:
    """按位置列表拆分文本。"""
    if not positions:
        return [text]

    parts: list[str] = []
    prev_end = 0

    for pos in positions:
        part = text[prev_end:pos].strip()
        if part:
            parts.append(part)
        prev_end = pos

    remaining = text[prev_end:].strip()
    if remaining:
        parts.append(remaining)

    return parts


# ── Step 2: 单行选项行内切分 ──────────────────────────────────────


def _expand_inline_option_lines(lines: list[L1Line]) -> list[L1Line]:
    """将单行多选项切分为多行。

    处理场景：'A.充分不必要条件B.必要不充分条件C.充要条件D.既不充分也不必要条件'
    期望结果：4 行，每行一个选项

    遵守 V1_LESSONS 3.21。
    """
    result: list[L1Line] = []

    for line in lines:
        text = line.text

        # table block 的单元格可能含 A./B./C./D.，不应按选项切分。
        if line.block_type == "table":
            result.append(line)
            continue

        # 检查是否是单行多选项
        option_positions = _find_inline_options(text)

        if len(option_positions) < 2:
            result.append(line)
            continue

        # 拆分选项
        parts = _split_options_at_positions(text, option_positions)

        for i, part in enumerate(parts):
            part = part.strip()
            if not part:
                continue

            new_line = L1Line(
                line_id="",
                page_no=line.page_no,
                line_no_in_page=0,
                order=0,
                text=part,
                block_type=line.block_type,
                bbox=line.bbox if i == 0 else None,
                source=line.source,
                continuation=line.continuation,
                raw_sources=dict(line.raw_sources) if line.raw_sources else {},
                selected_source=line.selected_source,
                evidence=line.evidence,
                confidence=line.confidence,
            )
            result.append(new_line)

    return result


def _find_inline_options(text: str) -> list[int]:
    """找到行内所有选项标记的位置。

    支持两种格式：
    - A. xxx / A、xxx（点号/顿号分隔）
    - (A) xxx / （A）xxx（括号格式）
    """
    positions = []
    for match in _INLINE_OPTIONS_PATTERN.finditer(text):
        positions.append(match.start())
    for match in _PAREN_OPTIONS_PATTERN.finditer(text):
        pos = match.start()
        # 避免重复（如果已被点号格式匹配）
        if pos not in positions:
            positions.append(pos)
    positions.sort()
    return positions


def _split_options_at_positions(text: str, positions: list[int]) -> list[str]:
    """按选项位置拆分文本。"""
    parts: list[str] = []
    prev_end = 0

    for pos in positions:
        part = text[prev_end:pos].strip()
        if part:
            parts.append(part)
        prev_end = pos

    remaining = text[prev_end:].strip()
    if remaining:
        parts.append(remaining)

    return parts


# ── Step 3: 重编行号 ──────────────────────────────────────────────


def _renumber_lines(lines: list[L1Line], source: str) -> list[L1Line]:
    """重编行号，确保连续不跳号。"""
    pages: dict[int, list[L1Line]] = {}
    for line in lines:
        pages.setdefault(line.page_no, []).append(line)

    result: list[L1Line] = []
    global_order = 1

    for page_no in sorted(pages.keys()):
        page_lines = pages[page_no]
        prefix = _page_line_id_prefix(page_lines)
        for line_no, line in enumerate(page_lines, start=1):
            new_line = L1Line(
                line_id=f"{prefix}{page_no}L{line_no:03d}",
                page_no=page_no,
                line_no_in_page=line_no,
                order=global_order,
                text=line.text,
                block_type=line.block_type,
                bbox=line.bbox,
                source=line.source,
                continuation=line.continuation,
                raw_sources=dict(line.raw_sources) if line.raw_sources else {},
                selected_source=line.selected_source,
                evidence=line.evidence,
                confidence=line.confidence,
            )
            result.append(new_line)
            global_order += 1

    return result


def _page_line_id_prefix(page_lines: list[L1Line]) -> str:
    """按来源确定页内行号前缀。

    Native 生成阶段使用 N，PP-StructureV3 使用 P。优先沿用原始行的前缀，
    便于兼容手工构造且仍以 P 为前缀的既有测试 fixture。
    """
    for line in page_lines:
        if line.line_id and line.line_id[0] in ("P", "N"):
            return line.line_id[0]
    if page_lines and page_lines[0].source == "native":
        return "N"
    return "P"


# ── Step 4: 同步 pages 行引用 ──────────────────────────────────────


def _sync_pages_lines(pages: list, canonical_lines: list[L1Line]) -> list:
    """同步 pages 的行引用为 canonical lines。

    确保 pages[].lines 与 L1Document.lines 一致。
    """
    # 按页码分组 canonical lines
    lines_by_page: dict[int, list[L1Line]] = {}
    for line in canonical_lines:
        lines_by_page.setdefault(line.page_no, []).append(line)

    # 更新每个 page 的 lines
    updated_pages = []
    for page in pages:
        page_lines = lines_by_page.get(page.page_no, [])
        updated_page = type(page)(
            page_no=page.page_no,
            lines=page_lines,
            images=page.images,
        )
        updated_pages.append(updated_page)

    return updated_pages

"""
OCR-to-L1 统一转换接口。

将 OcrDocument 转换为 L1Document，供 pipeline 使用。
ppsv3_l1.extract_l1_from_ocr() 委托给此模块。
"""

from __future__ import annotations

import re

from app.domains.document.l1_postprocessor import postprocess_l1
from app.domains.document.schemas_l1 import L1Document, L1Image, L1Line, L1Page
from app.domains.document.schemas import OcrDocument

# LaTeX formula markers
_FORMULA_RE = re.compile(r"\$\$[^$]+\$\$|\$[^$]+\$|\\\(|\\\[|\\begin\{")


def convert_ocr_to_l1(
    ocr_doc: OcrDocument,
    *,
    filename: str | None = None,
) -> L1Document:
    """将 PP-StructureV3 OCR 输出转换为 L1Document。

    优先使用 OcrPage.blocks（含 bbox）构建 L1Line；
    若 blocks 为空（如 fixture 数据），回退到 markdown 拆分（bbox=None）。
    """
    fname = filename or ocr_doc.filename
    pages: list[L1Page] = []
    all_lines: list[L1Line] = []
    all_images: list[L1Image] = []
    global_order = 1

    for ocr_page in ocr_doc.pages:
        page_no = ocr_page.page_number
        page_lines: list[L1Line] = []

        if ocr_page.blocks:
            # 有 block 级数据：按 block 构建 L1Line（带 bbox）
            # VL 输出的 block 可能包含多行（题干+选项合并），需按 \n 拆分；
            # table block 必须整块保留，避免 <table> 结构被拆成多个 L1Line。
            line_no = 0
            for block in ocr_page.blocks:
                raw_text = block.content.strip()
                if not raw_text:
                    continue
                for sub_text in _split_block_lines(block):
                    line_no += 1
                    block_type = _map_block_type(block.label)
                    line = L1Line(
                        line_id="", page_no=page_no, line_no_in_page=line_no,
                        order=global_order, text=sub_text, block_type=block_type,
                        bbox=block.bbox, source="ppsv3",
                    )
                    page_lines.append(line)
                    all_lines.append(line)
                    global_order += 1
        else:
            # 无 block 数据：回退到 markdown 拆分
            raw_texts = _split_markdown_lines(ocr_page.markdown)
            line_no = 0
            for text in raw_texts:
                text = text.strip()
                if not text:
                    continue
                line_no += 1
                block_type = _infer_block_type(text)
                line = L1Line(
                    line_id="", page_no=page_no, line_no_in_page=line_no,
                    order=global_order, text=text, block_type=block_type,
                    bbox=None, source="ppsv3",
                )
                page_lines.append(line)
                all_lines.append(line)
                global_order += 1

        page_images: list[L1Image] = []
        for img in ocr_page.images:
            image = L1Image(
                image_id=f"P{page_no}IMG{len(page_images)+1:03d}",
                page_no=page_no, bbox=img.bbox, xref=None,
                source="ppsv3", url=img.url, placement="unknown",
            )
            page_images.append(image)
            all_images.append(image)

        pages.append(L1Page(page_no=page_no, lines=page_lines, images=page_images))

    raw_doc = L1Document(
        filename=fname, pages=pages, lines=all_lines, images=all_images,
        source="ppsv3", total_pages=len(ocr_doc.pages),
        text_coverage=1.0, raw_lines=list(all_lines),
    )
    return postprocess_l1(raw_doc)


def _map_block_type(label: str) -> str:
    """将 PP block_label 映射为 L1Line block_type。"""
    label_lower = label.lower()
    if "formula" in label_lower:
        return "formula"
    if "table" in label_lower:
        return "table"
    if "figure" in label_lower or "image" in label_lower:
        return "figure_placeholder"
    return "text"


def _split_block_lines(block) -> list[str]:
    """将 OCR block 拆成 L1 行文本。

    table block 是结构化整体：PP/VL 常返回带换行的 HTML <table>，
    若按 \\n 拆分会破坏 answer_matcher 对整张表格的解析。这里保持为单行，
    同时压缩空白，使后续 L1 处理可把表格当成一个稳定行。

    例外（2026-08-26，LOG v6.37）：**选项表**（选项标签 A/B/C/D 在表格内部，
    即 `<td>A</td>` 作为表格行的一部分）需要拆行——否则 LLM 无法给选项
    独立行号 → options_line_ids 全空 → 锚点校验 retry（化学表格选项题）。
    拆行格式：`<td>A</td>` → `A. ` 前缀，其余 `<td>` 用 `，` 合并（保留
    VL 公式文本），满足 _STRICT_OPTION_LABEL_RE 与 _strip_option_label。
    资料表/答案表（选项在表外或单元格内容是数据）保持单行。
    """
    if _map_block_type(block.label) == "table":
        text = block.content.strip()
        if not text:
            return []
        return _split_option_table(text)

    return [
        sub_text.strip()
        for sub_text in block.content.split("\n")
        if sub_text.strip()
    ]


def _infer_block_type(text: str) -> str:
    """从文本内容推断 block_type。"""
    if "<table" in text.lower():
        return "table"
    if _FORMULA_RE.search(text):
        return "formula"
    return "text"


# 选项标签：A / A. / A． 等（表格单元格内的选项标签）
# 两种形态：纯标签 `<td>A</td>`，或带内容 `<td>A. 制备...`
_OPTION_TAG_RE = re.compile(r"^\s*([A-G])\s*[.、．]?\s*$")
_OPTION_PREFIX_RE = re.compile(r"^\s*([A-G])\s*[.、．]\s*")


def _is_option_table(html: str) -> bool:
    """判断 HTML table 是否为"选项表"（选项标签在表格内部）。

    判据（2026-08-26 调查真实 VL 输出）：
    - **五行选项表**（Q8/Q12 等，每个选项独立一行）：≥2 行首列为
      A-G 纯标签（`<td>A</td>`）
    - **2×2 图+文选项表**（Q10 等，一行内 4 个 `<td>A. 制备...`）：
      首行首列是带内容的选项前缀（`A. `）
    - **标签行+内容行表**（二附中 Q14：第一行 `<td>A</td><td>B</td><td>C</td><td>D</td>`
      纯标签行，第二行是各选项内容）：
      任意行内 ≥2 个纯 A-G 标签单元格
    - **表头+选项行表**（大兴 Q1：`<td>材料</td><td>攀岩场光伏板</td>...`
      第二行 `<td>主要成分</td><td>A.单晶硅</td>...`）：行内 ≥2 个
      带内容的选项前缀单元格（非首列也算）
    满足其一 → 选项表（拆行）；否则 → 资料表/答案表（保持单行）。

    不拆的表格（真实形态验证）：
    - 答案表（T8）：首列是"题号/答案"字样，单元格是单字母数据
    - 资料表（T3-T7）：无 A-G 标签或标签非选项形态
    """
    tag_rows = 0
    first_row_prefix = False
    any_inline_prefix = False
    any_pure_tag_row = False
    for ri, row_html in enumerate(_TR_RE.findall(html)):
        tds = _TD_RE.findall(row_html)
        if len(tds) < 2:
            continue
        cells = [_cell_text(td) for td in tds]
        # 答案表（含"题号/答案"表头）排除：单元格 A/B/C/D 是答案数据非选项
        if any(c in ("题号", "答案") for c in cells[:2]):
            return False
        first_cell = cells[0]
        if _OPTION_TAG_RE.match(first_cell):
            tag_rows += 1
        elif ri == 0 and _OPTION_PREFIX_RE.match(first_cell):
            first_row_prefix = True
        # 行内 ≥2 个纯 A-G 标签（二附中 Q14 标签行 `A|B|C|D`）
        pure_tag_count = sum(1 for c in cells if _OPTION_TAG_RE.match(c))
        if pure_tag_count >= 2:
            any_pure_tag_row = True
        # 行内 ≥2 个带内容前缀（选项标签出现在非首列，如大兴 Q1 表）
        prefix_count = sum(1 for c in cells if _OPTION_PREFIX_RE.match(c))
        if prefix_count >= 2:
            any_inline_prefix = True
    return (tag_rows >= 2 or first_row_prefix
            or any_inline_prefix or any_pure_tag_row)


# 表格行/单元格拆分（与 answer_matcher 共用同构正则）
_TR_RE = re.compile(r"<tr>(.*?)</tr>", re.DOTALL)
_TD_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.DOTALL)


def _cell_text(td_html: str) -> str:
    """单元格去 HTML 标签但保留 <img> 引用（图片是选项的组成部分）。

    普通标签（`<td>` 内嵌 `<i>`/`<b>` 等）剥掉；`<img src=.../>` 引用
    整体保留（选项表拆行后图片引用随行保留，供 question_images 关联）。
    """
    return re.sub(r"<(?!img\b)[^>]+>", "", td_html).strip()


def _split_option_table(html: str) -> list[str]:
    """选项表拆行：每行一个选项，格式 `A. <内容>`。

    支持三种形态：
    1. 每行一选项（Q8/Q12 五行表）：`<td>A</td><td>内容1</td><td>内容2</td>`
       → `A. 内容1，内容2`
    2. 同行多选项（Q10 2×2、大兴 Q1）：`<td>A. 制备</td><td>B. 制备</td>...`
       → 每单元格一行
    3. 标签行+内容行（二附中 Q14）：第一行 `<td>A</td><td>B</td>...`，
       第二行是各选项内容 → 标签行与内容行按列配对
    非选项表返回压缩后的单行，保持原行为。
    """
    if not _is_option_table(html):
        return [" ".join(html.split())]

    rows: list[list[str]] = []
    for row_html in _TR_RE.findall(html):
        tds = _TD_RE.findall(row_html)
        if not tds:
            continue
        # 单元格去 HTML 标签但保留 <img> 引用（图片是选项的组成部分）
        rows.append([_cell_text(td) for td in tds])

    # 形态 2：任意行内 ≥2 个带内容前缀 → 每单元格一行
    for texts in rows:
        prefix_cells = [t for t in texts if _OPTION_PREFIX_RE.match(t)]
        if len(prefix_cells) >= 2:
            out: list[str] = []
            for texts2 in rows:
                p2 = [t for t in texts2 if _OPTION_PREFIX_RE.match(t)]
                if len(p2) >= 2:
                    for t in texts2:
                        if t:
                            out.append(t)
                else:
                    row_text = "，".join(t for t in texts2 if t)
                    if row_text:
                        out.append(row_text)
            return [l for l in out if l.strip()]

    # 形态 3：首行是 ≥2 个纯标签（`A|B|C|D`）→ 标签行与后续内容行按列配对
    if rows and len(rows[0]) >= 2:
        first_cells = rows[0]
        pure_tags = [c for c in first_cells if _OPTION_TAG_RE.match(c)]
        if len(pure_tags) >= 2:
            # 标签行 → 每标签一行；后续行内容按列并入对应标签
            label_map: list[tuple[str, str]] = []
            for ci, cell in enumerate(first_cells):
                m = _OPTION_TAG_RE.match(cell)
                if m:
                    content_parts: list[str] = []
                    for texts in rows[1:]:
                        if ci < len(texts) and texts[ci]:
                            content_parts.append(texts[ci])
                    label_map.append((m.group(1), "，".join(content_parts)))
            out = [f"{label}. {content}" if content else f"{label}."
                   for label, content in label_map]
            return [l for l in out if l.strip()]

    # 形态 1：每行一选项
    lines: list[str] = []
    for texts in rows:
        first = texts[0]
        m_tag = _OPTION_TAG_RE.match(first)
        m_pre = _OPTION_PREFIX_RE.match(first)
        if (m_tag or m_pre) and len(texts) >= 2:
            label = (m_tag or m_pre).group(1)
            if m_tag:
                # 纯标签 `<td>A</td>`：前缀 `A. ` + 其余列内容
                rest = [t for t in texts[1:] if t]
                content = "，".join(rest)
                lines.append(f"{label}. {content}" if content else f"{label}.")
            else:
                # 首列已含内容 `<td>A. 制备...`：保留原文（其他列并入）
                rest = [t for t in texts[1:] if t]
                content = "，".join(rest)
                lines.append(f"{first}，{content}" if content else first)
        else:
            # 表头行/资料行/图片行：作为独立行
            row_text = "，".join(t for t in texts if t)
            if row_text:
                lines.append(row_text)
    return [l for l in lines if l.strip()]


def _split_markdown_lines(markdown: str) -> list[str]:
    """无 block 数据时按行拆分 markdown，但跨行 HTML table 必须合并。

    PP/VL 的 markdown fallback 同样可能把 `<html><body><table>...` 拆成多行；
    若逐行生成 L1Line，table 结构会再次被破坏，因此这里把从 `<table>` 到
    `</table>` 的连续片段合并为一条 L1 行。

    2026-08-26（LOG v6.37）：合并后的选项表（选项标签在表格内部）再拆行，
    使 LLM 能对选项给独立行号（化学表格选项题锚点修复）。
    """
    lines = markdown.splitlines()
    result: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            continue

        if _is_table_start(line):
            parts = [line]
            index += 1
            while index < len(lines) and "</table>" not in lines[index]:
                if lines[index].strip():
                    parts.append(lines[index].strip())
                index += 1
            if index < len(lines):
                parts.append(lines[index].strip())
                index += 1
            joined = " ".join(parts)
            # 选项表拆行；资料表保持单行
            if "<table" in joined.lower():
                result.extend(_split_option_table(joined))
            else:
                result.append(joined)
            continue

        result.append(line)
        index += 1

    return result


def _is_table_start(text: str) -> bool:
    """判断 markdown 行是否是 HTML table 的起点。"""
    lowered = text.lower()
    return "<table" in lowered or (
        "<html" in lowered and "<body" in lowered and "table" in lowered
    )

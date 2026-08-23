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
    """
    if _map_block_type(block.label) == "table":
        text = block.content.strip()
        if not text:
            return []
        return [" ".join(text.split())]

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


def _split_markdown_lines(markdown: str) -> list[str]:
    """无 block 数据时按行拆分 markdown，但跨行 HTML table 必须合并。

    PP/VL 的 markdown fallback 同样可能把 `<html><body><table>...` 拆成多行；
    若逐行生成 L1Line，table 结构会再次被破坏，因此这里把从 `<table>` 到
    `</table>` 的连续片段合并为一条 L1 行。
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
            result.append(" ".join(parts))
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

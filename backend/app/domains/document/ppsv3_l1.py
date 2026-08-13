"""PP-StructureV3 L1 generator."""

from __future__ import annotations

import logging
import re

from app.domains.document.l1_postprocessor import postprocess_l1
from app.domains.document.schemas_l1 import L1Document, L1Image, L1Line, L1Page
from app.domains.document.schemas import OcrDocument

logger = logging.getLogger(__name__)

# LaTeX formula markers
_FORMULA_RE = re.compile(r"$$|\(|\[|\begin\{")
# Table rows
_TABLE_RE = re.compile(r"^\|.*\|")

def extract_l1_from_ocr(
    ocr_doc: OcrDocument,
    *,
    filename: str | None = None,
) -> L1Document:
    """Convert PP-StructureV3 OCR output to L1Document.

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
            line_no = 0
            for block in ocr_page.blocks:
                text = block.content.strip()
                if not text:
                    continue
                line_no += 1
                block_type = _map_block_type(block.label)
                line = L1Line(
                    line_id="", page_no=page_no, line_no_in_page=line_no,
                    order=global_order, text=text, block_type=block_type,
                    bbox=block.bbox, source="ppsv3",
                )
                page_lines.append(line)
                all_lines.append(line)
                global_order += 1
        else:
            # 无 block 数据：回退到 markdown 拆分
            raw_texts = ocr_page.markdown.splitlines()
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


def _infer_block_type(text: str) -> str:
    """Infer block_type from text content."""
    if _FORMULA_RE.search(text):
        return "formula"
    if _TABLE_RE.search(text):
        return "table"
    return "text"

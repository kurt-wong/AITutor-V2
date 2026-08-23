"""
Native PDF L1 生成器 — PyMuPDF 文本层提取 → L1Document。

按阅读顺序提取文本块，生成 L1Line/L1Page/L1Image，
图片 bbox 通过 get_image_rects(xref) 获取。

详见 Docs/01_Product/T3_IMPLEMENTATION.md §8 Task 1.1。
遵守 V1_LESSONS 3.27（图片 bbox 获取方式）。
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.domains.document.l1_postprocessor import postprocess_l1
from app.domains.document.schemas_l1 import L1Document, L1Image, L1Line, L1Page

logger = logging.getLogger(__name__)

# 页眉页脚过滤阈值
_PAGE_HEADER_Y_MAX = 15
_PAGE_FOOTER_Y_MIN = 800


def extract_l1_from_pdf(
    pdf_path: Path,
    *,
    filename: str | None = None,
    page_range: tuple[int, int] | None = None,
) -> L1Document:
    """从 PDF 提取 L1Document。

    Args:
        pdf_path: PDF 文件路径
        filename: 文件名（默认使用 Path.name）
        page_range: 页码范围 (start, end)，1-based，包含两端。None 表示全部页面。

    Returns:
        L1Document：后处理后的 L1 文档
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise ImportError(
            "PyMuPDF 未安装，请运行: pip install pymupdf"
        )

    doc = fitz.open(str(pdf_path))
    total_pdf_pages = doc.page_count
    fname = filename or pdf_path.name

    # 确定提取范围
    if page_range:
        start_idx = max(0, page_range[0] - 1)
        end_idx = min(total_pdf_pages, page_range[1])
    else:
        start_idx = 0
        end_idx = total_pdf_pages

    pages: list[L1Page] = []
    all_lines: list[L1Line] = []
    all_images: list[L1Image] = []
    global_order = 1

    for page_idx in range(start_idx, end_idx):
        page = doc[page_idx]
        page_no = page_idx + 1  # 1-based

        # 提取文本块
        text_dict = page.get_text("dict")
        blocks = text_dict["blocks"]

        # 分离文本块和图片块
        content_blocks: list[dict] = []
        page_image_xrefs: set[int] = set()

        for block in blocks:
            bbox = block["bbox"]

            if block["type"] == 0:  # 文本块
                # 过滤页眉页脚
                if bbox[1] > _PAGE_FOOTER_Y_MIN or bbox[3] < _PAGE_HEADER_Y_MAX:
                    continue

                # 合并 spans 为块文本
                parts: list[str] = []
                for line_info in block.get("lines", []):
                    line_text = "".join(
                        s["text"] for s in line_info.get("spans", [])
                    )
                    parts.append(line_text)
                text = " ".join(parts).strip()

                if text and len(text) > 0:
                    content_blocks.append({
                        "bbox": bbox,
                        "text": text,
                        "y": bbox[1],
                    })

            elif block["type"] == 1:  # 图块
                if bbox[1] > _PAGE_FOOTER_Y_MIN:
                    continue

                # 获取图片 xref
                img_list = page.get_images(full=True)
                for img_info in img_list:
                    xref = img_info[0]
                    if xref in page_image_xrefs:
                        continue
                    rects = page.get_image_rects(xref)
                    for rect in rects:
                        if (
                            abs(rect.x0 - bbox[0]) < 5
                            and abs(rect.y0 - bbox[1]) < 5
                        ):
                            img_id = f"P{page_no}IMG{len(all_images) + 1:03d}"
                            all_images.append(
                                L1Image(
                                    image_id=img_id,
                                    page_no=page_no,
                                    bbox={
                                        "x1": round(rect.x0, 1),
                                        "y1": round(rect.y0, 1),
                                        "x2": round(rect.x1, 1),
                                        "y2": round(rect.y1, 1),
                                    },
                                    xref=xref,
                                    source="native",
                                    placement="unknown",
                                )
                            )
                            page_image_xrefs.add(xref)
                            break

        # 按 y 坐标排序（阅读顺序）
        content_blocks.sort(key=lambda b: b["y"])

        # 生成 L1Line
        page_lines: list[L1Line] = []
        for block in content_blocks:
            line_no = len(page_lines) + 1
            line = L1Line(
                line_id=f"N{page_no}L{line_no:03d}",
                page_no=page_no,
                line_no_in_page=line_no,
                order=global_order,
                text=block["text"],
                block_type="text",
                bbox={
                    "x1": round(block["bbox"][0], 1),
                    "y1": round(block["bbox"][1], 1),
                    "x2": round(block["bbox"][2], 1),
                    "y2": round(block["bbox"][3], 1),
                },
                source="native",
                continuation=False,
            )
            page_lines.append(line)
            all_lines.append(line)
            global_order += 1

        pages.append(
            L1Page(page_no=page_no, lines=page_lines, images=[])
        )

    doc.close()

    # 计算文本层覆盖率
    text_coverage = _calculate_text_coverage(
        pdf_path, start_idx, end_idx
    )

    # 构建原始 L1Document
    raw_doc = L1Document(
        filename=fname,
        pages=pages,
        lines=all_lines,
        images=all_images,
        source="native",
        total_pages=end_idx - start_idx,
        text_coverage=text_coverage,
    )

    logger.info(
        "native_extract filename=%s pages=%d lines=%d images=%d "
        "text_coverage=%.2f",
        fname,
        end_idx - start_idx,
        len(all_lines),
        len(all_images),
        text_coverage,
    )

    # 执行后处理
    return postprocess_l1(raw_doc)


def _calculate_text_coverage(
    pdf_path: Path, start_idx: int, end_idx: int
) -> float:
    """计算文本层覆盖率。

    覆盖率 = 有文本的页数 / 总页数。
    用于判断是否需要 OCR fallback。
    """
    try:
        import fitz

        doc = fitz.open(str(pdf_path))
        total = end_idx - start_idx
        if total == 0:
            doc.close()
            return 0.0

        has_text = 0
        for i in range(start_idx, end_idx):
            text = doc[i].get_text().strip()
            if text and len(text) > 10:
                has_text += 1
        doc.close()
        return round(has_text / total, 4)
    except Exception:
        return 0.0

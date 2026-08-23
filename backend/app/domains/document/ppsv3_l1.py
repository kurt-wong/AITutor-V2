"""PP-StructureV3 L1 generator."""

from __future__ import annotations

import logging

from app.domains.document.schemas_l1 import L1Document
from app.domains.document.schemas import OcrDocument

logger = logging.getLogger(__name__)


def extract_l1_from_ocr(
    ocr_doc: OcrDocument,
    *,
    filename: str | None = None,
) -> L1Document:
    """Convert PP-StructureV3 OCR output to L1Document.

    委托给 ocr_l1_converter.convert_ocr_to_l1()（H6 修复）。
    """
    from app.domains.document.ocr_l1_converter import convert_ocr_to_l1
    return convert_ocr_to_l1(ocr_doc, filename=filename)

"""
DEPRECATED — 当前为临时验证路径，正式 T3 管线将重写本文件。

当前实现：OCR → LLM 直接输出内容（违反 V1_LESSONS 3.1）。
正式实现：Native/OCR → L1 → LLM 标注 → 锚点校正 → 切片 → 答案匹配。

详见 Docs/01_Product/T3_IMPLEMENTATION.md。
"""

import os

# 运行时拦截：正式环境禁止导入此模块
if os.environ.get("APP_ENV") == "production":
    raise ImportError(
        "parser.py 已废弃，禁止在正式环境使用。"
        "请使用 T3 管线：line_annotator.py + anchor_corrector.py + content_slicer.py + answer_matcher.py"
    )

from pathlib import Path

from app.domains.document.ocr.providers import OCRFallbackChain, build_ocr_chain
from app.domains.document.question_extractor import LLMQuestionExtractor
from app.domains.document.schemas import QuestionAggregate


class DocumentParser:
    def __init__(
        self,
        *,
        ocr_chain: OCRFallbackChain | None = None,
        question_extractor: LLMQuestionExtractor | None = None,
    ) -> None:
        self.ocr_chain = ocr_chain or build_ocr_chain()
        self.question_extractor = question_extractor or LLMQuestionExtractor()

    async def parse_pdf(
        self,
        file_path: Path,
        *,
        filename: str | None = None,
        subject: str | None = None,
        grade: str | None = None,
        year: int | None = None,
        school: str | None = None,
    ) -> QuestionAggregate:
        ocr_document = await self.ocr_chain.extract(file_path)
        page_blocks: list[str] = []
        for page in ocr_document.pages:
            image_refs = "\n".join(
                f"图片引用: {image.id}" for image in page.images
            )
            page_block = f"# 第 {page.page_number} 页\n\n{page.markdown}"
            if image_refs:
                page_block = f"{page_block}\n{image_refs}"
            page_blocks.append(page_block)

        metadata = {
            "subject": subject,
            "grade": grade,
            "year": year,
            "school": school,
        }
        aggregate = await self.question_extractor.extract(
            filename=filename or file_path.name,
            markdown="\n\n".join(page_blocks),
            metadata=metadata,
        )
        aggregate.provider = ocr_document.provider_used
        return aggregate

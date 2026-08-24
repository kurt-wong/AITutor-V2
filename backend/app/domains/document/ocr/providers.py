import base64
import logging
import mimetypes
from pathlib import Path
from typing import Protocol, Sequence, runtime_checkable

from app.ai.gateway import LLMGateway
from app.ai.providers import HTTPLLMProvider
from app.core.config import settings
from app.domains.document.ocr.paddle_client import PaddleOCRClient, PaddleOCRQueue
from app.domains.document.schemas import OcrDocument, OcrPage

logger = logging.getLogger(__name__)


class OCRProviderError(RuntimeError):
    """所有 OCR provider 失败时抛出；failures 保留每个 provider 的失败明细。"""

    def __init__(
        self,
        message: str,
        failures: list[tuple[str, str]] | None = None,
    ) -> None:
        super().__init__(message)
        self.failures = failures or []


class OCROutageError(OCRProviderError):
    """主 OCR（paddle 系）不可用，任务应标记 ocr_unavailable 等待恢复。

    2026-08-25 用户决策（OCR_PROVIDER_POLICY.md）：paddle（PPS/PVL）是唯一
    L1 识别提供方，失败/熔断耗尽后**不降级 LLM VL**——LLM VL 只做可选交叉
    验证，不驱动入库。任务失败原因带 ocr_unavailable，等 paddle 恢复后重跑。
    """

    def __init__(
        self,
        message: str,
        failures: list[tuple[str, str]] | None = None,
    ) -> None:
        super().__init__(message, failures)


@runtime_checkable
class OCRProvider(Protocol):
    name: str

    async def extract(self, file_path: Path) -> OcrDocument:
        ...


class MockOCRProvider:
    name = "mock"

    def __init__(self, markdown: str = "") -> None:
        self.markdown = markdown or (
            "# Mock Page\n\n"
            "1. 示例题干：函数 f(x)=x^2 的最小值是多少？\n\n"
            "A. 0\nB. 1\nC. -1\nD. 2\n\n"
            "答案：A\n解析：x^2 的最小值为 0。"
        )

    async def extract(self, file_path: Path) -> OcrDocument:
        return OcrDocument(
            filename=file_path.name,
            pages=[
                OcrPage(
                    page_number=1,
                    markdown=self.markdown,
                    source_provider=self.name,
                )
            ],
            provider_used=self.name,
        )


class LLMVisionOCRProvider:
    """LLM 视觉 OCR provider（mimo-vl / deepseek-vl）。

    快速失败：任一页失败（gateway 内部已重试 3 次）→ 抛异常放弃该 provider，
    让 OCRFallbackChain 立即降级到下一个 VL provider。
    原因：VL API 服务端间歇性不稳定（如 mimo-vl 断连），
    逐页重试 3 次 × 多页会浪费大量时间，快速降级更可靠。
    """

    def __init__(self, *, name: str, gateway: LLMGateway) -> None:
        self.name = name
        self.gateway = gateway

    async def extract(self, file_path: Path) -> OcrDocument:
        pages: list[OcrPage] = []
        if file_path.suffix.lower() == ".pdf":
            rendered_pages = _render_pdf_pages(file_path)
            for page_no, image_data_url in enumerate(rendered_pages, start=1):
                prompt = (
                    f"OCR page {page_no} completely to Markdown. "
                    "Keep question numbers, stems, options, answers, explanations, "
                    "formulas, tables, and image references. Output only Markdown."
                )
                try:
                    markdown = await self.gateway.complete_vision(
                        prompt,
                        image_data_url,
                        temperature=0.0,
                    )
                except Exception as exc:
                    # gateway 内部已重试 3 次仍失败 → 放弃本 provider，降级下一个
                    logger.warning(
                        "vl provider=%s page=%d failed after gateway retries, "
                        "falling back to next provider: %s",
                        self.name, page_no, exc,
                    )
                    raise
                pages.append(
                    OcrPage(
                        page_number=page_no,
                        markdown=markdown,
                        source_provider=self.name,
                    )
                )
        else:
            image_data_url = _data_url(file_path)
            prompt = (
                "OCR this image completely to Markdown. "
                "Keep question numbers, stems, options, answers, explanations, "
                "formulas, tables, and image references. Output only Markdown."
            )
            markdown = await self.gateway.complete_vision(
                prompt,
                image_data_url,
                temperature=0.0,
            )
            pages.append(
                OcrPage(
                    page_number=1,
                    markdown=markdown,
                    source_provider=self.name,
                )
            )
        return OcrDocument(
            filename=file_path.name,
            pages=pages,
            provider_used=self.name,
        )


class QueuedPaddleOCRProvider:
    """PaddleOCRQueue 的适配器，实现 OCRProvider 接口。

    用于 VL 模型的并发控制：当 model 包含 "VL" 时，
    用 PaddleOCRQueue 包装 client，限制并发为 1。
    """

    def __init__(self, client: PaddleOCRClient, max_concurrent: int = 1) -> None:
        self._queue = PaddleOCRQueue(client, max_concurrent=max_concurrent)
        self.name = client.name
        self.model = client.model

    async def extract(self, file_path: Path) -> OcrDocument:
        """实现 OCRProvider.extract() 接口。"""
        return await self._queue.submit(file_path, model=self.model)

    def close(self) -> None:
        """关闭底层队列，取消后台 worker。"""
        self._queue.close()


class OCRFallbackChain:
    def __init__(self, providers: Sequence[OCRProvider]) -> None:
        self.providers = list(providers)

    async def extract(self, file_path: Path) -> OcrDocument:
        failures: list[tuple[str, str]] = []
        for provider in self.providers:
            try:
                document = await provider.extract(file_path)
                document.provider_used = provider.name
                return document
            except Exception as exc:
                failures.append((provider.name, str(exc)))
                logger.warning("ocr provider=%s failed: %s", provider.name, exc)
        detail = "; ".join(f"{name}: {message}" for name, message in failures)
        # 2026-08-25：链只含 paddle（LLM VL 已移出驱动链），全部失败即
        # OCROutageError → 任务标记 ocr_unavailable 等待 paddle 恢复，不降级。
        raise OCROutageError(
            f"all OCR providers failed ({detail or 'none configured'})",
            failures=failures,
        )

    def close(self) -> None:
        """释放 provider 持有的后台资源（目前是 VL 队列 worker）。"""
        for provider in self.providers:
            close = getattr(provider, "close", None)
            if callable(close):
                close()


def build_ocr_chain(
    *,
    mock: bool | None = None,
    model: str | None = None,
) -> OCRFallbackChain:
    """构建 OCR 链。

    2026-08-25 用户决策（OCR_PROVIDER_POLICY.md §2）：L1 识别仅用 paddle 系
    （PP-StructureV3 / PaddleOCR-VL）；**LLM VL（mimo-vl / deepseek-vl）移出
    驱动链**——不在此追加，只保留 LLMVisionOCRProvider 类作为可选交叉验证
    入口（由外部显式构造）。paddle 不可用时 OCRFallbackChain 抛
    OCROutageError，任务标记 ocr_unavailable 等待恢复，不降级。
    """
    use_mock = settings.ocr_mock_mode if mock is None else mock
    if use_mock:
        return OCRFallbackChain([MockOCRProvider()])

    providers: list[OCRProvider] = []
    if settings.paddleocr_vl_token:
        paddle_kwargs: dict = dict(
            base_url=settings.paddleocr_api_base_url,
            token=settings.paddleocr_vl_token,
            timeout_seconds=settings.llm_request_timeout_seconds,
            poll_interval_seconds=settings.paddleocr_poll_interval_seconds,
            job_timeout_seconds=settings.paddleocr_job_timeout_seconds,
        )
        if model is not None:
            paddle_kwargs["model"] = model

        paddle_client = PaddleOCRClient(**paddle_kwargs)

        # 所有 PaddleOCR 模型（PPS 和 VL）都走本地队列（max_concurrent=1）。
        # 原因：paddle AIStudio API 服务端队列容量有限（code 10010 队列满），
        # 客户端排队可避免多 worker/多文档并发提交打爆服务端队列。
        # 历史：VL 模型已排队（2026-08-18），PPS 未排队导致并发提交触发 10010。
        logger.info(
            "Using queued PaddleOCR provider for model: %s (max_concurrent=1)",
            model or "PP-StructureV3",
        )
        providers.append(QueuedPaddleOCRProvider(paddle_client, max_concurrent=1))

    # 不再追加 mimo-vl / deepseek-vl（2026-08-25 用户决策）。
    # LLMVisionOCRProvider 保留实现，仅用于可选交叉验证（外部显式构造）。
    return OCRFallbackChain(providers)


def _data_url(path: Path) -> str:
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


_VISION_PDF_ZOOM = 2.0
_VISION_PDF_MAX_PAGES = 50


def _render_pdf_pages(path: Path) -> list[str]:
    """Render PDF pages to PNG data URLs for vision LLM OCR fallback."""
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise OCRProviderError(
            "PyMuPDF is required for PDF vision OCR fallback"
        ) from exc

    try:
        doc = fitz.open(str(path))
    except Exception as exc:
        raise OCRProviderError(
            f"failed to open PDF for vision OCR: {exc}"
        ) from exc

    try:
        if doc.page_count < 1:
            raise OCRProviderError("PDF has no pages")
        if doc.page_count > _VISION_PDF_MAX_PAGES:
            raise OCRProviderError(
                f"PDF has {doc.page_count} pages, "
                f"above vision OCR limit {_VISION_PDF_MAX_PAGES}"
            )

        matrix = fitz.Matrix(_VISION_PDF_ZOOM, _VISION_PDF_ZOOM)
        pages: list[str] = []
        for page in doc:
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            png_bytes = pixmap.tobytes("png")
            encoded = base64.b64encode(png_bytes).decode("ascii")
            pages.append(f"data:image/png;base64,{encoded}")
        return pages
    finally:
        doc.close()

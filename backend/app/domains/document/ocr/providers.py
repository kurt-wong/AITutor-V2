import base64
import logging
import mimetypes
from pathlib import Path
from typing import Protocol, Sequence, runtime_checkable

from app.ai.gateway import LLMGateway
from app.ai.providers import HTTPLLMProvider
from app.core.config import settings
from app.domains.document.ocr.paddle_client import PaddleOCRClient
from app.domains.document.schemas import OcrDocument, OcrPage

logger = logging.getLogger(__name__)


class OCRProviderError(RuntimeError):
    pass


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
    def __init__(self, *, name: str, gateway: LLMGateway) -> None:
        self.name = name
        self.gateway = gateway

    async def extract(self, file_path: Path) -> OcrDocument:
        image_data_url = _data_url(file_path)
        prompt = (
            "请把这份文档完整 OCR 为 Markdown。"
            "保留题号、题干、选项、答案、解析、公式、表格和图片引用。"
            "只输出 Markdown，不要额外说明。"
        )
        markdown = await self.gateway.complete_vision(
            prompt,
            image_data_url,
            temperature=0.0,
        )
        return OcrDocument(
            filename=file_path.name,
            pages=[
                OcrPage(
                    page_number=1,
                    markdown=markdown,
                    source_provider=self.name,
                )
            ],
            provider_used=self.name,
        )


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
        raise OCRProviderError(f"all OCR providers failed ({detail or 'none configured'})")


def build_ocr_chain(*, mock: bool | None = None) -> OCRFallbackChain:
    use_mock = settings.ocr_mock_mode if mock is None else mock
    if use_mock:
        return OCRFallbackChain([MockOCRProvider()])

    providers: list[OCRProvider] = []
    if settings.paddleocr_vl_token:
        providers.append(
            PaddleOCRClient(
                base_url=settings.paddleocr_api_base_url,
                token=settings.paddleocr_vl_token,
                timeout_seconds=settings.llm_request_timeout_seconds,
                poll_interval_seconds=settings.paddleocr_poll_interval_seconds,
                job_timeout_seconds=settings.paddleocr_job_timeout_seconds,
            )
        )

    if settings.mimo_api_key and settings.mimo_base_url and settings.mimo_model:
        providers.append(
            LLMVisionOCRProvider(
                name="mimo",
                gateway=LLMGateway(
                    mode="live",
                    providers=[
                        HTTPLLMProvider(
                            name="mimo",
                            base_url=settings.mimo_base_url,
                            api_key=settings.mimo_api_key,
                            model=settings.mimo_model,
                            timeout_seconds=settings.llm_request_timeout_seconds,
                        )
                    ],
                ),
            )
        )

    if settings.qwen_vl_api_key and settings.qwen_vl_base_url and settings.qwen_vl_model:
        providers.append(
            LLMVisionOCRProvider(
                name="qwen_vl",
                gateway=LLMGateway(
                    mode="live",
                    providers=[
                        HTTPLLMProvider(
                            name="qwen_vl",
                            base_url=settings.qwen_vl_base_url,
                            api_key=settings.qwen_vl_api_key,
                            model=settings.qwen_vl_model,
                            timeout_seconds=settings.llm_request_timeout_seconds,
                        )
                    ],
                ),
            )
        )

    return OCRFallbackChain(providers)


def _data_url(path: Path) -> str:
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"

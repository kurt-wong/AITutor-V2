"""P0-D 测试：VL provider 快速失败降级。

背景：mimo-vl 服务端间歇性断连（RemoteProtocolError），8 页 PDF 逐页重试
3 次 × 8 页会浪费大量时间。LLMVisionOCRProvider 任一页失败（gateway 已重试
3 次）→ 抛异常，OCRFallbackChain 立即降级到下一个 provider。
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.document.ocr.providers import (
    LLMVisionOCRProvider,
    OCRFallbackChain,
    OCRProviderError,
)

_WORKSPACE_TMP = Path(__file__).resolve().parents[2] / "tmp" / "pytest_vl_fastfail"
_WORKSPACE_TMP.mkdir(parents=True, exist_ok=True)


class _FailingProvider:
    """总是失败的 OCR provider。"""

    def __init__(self, name: str, error: Exception) -> None:
        self.name = name
        self.error = error

    async def extract(self, file_path: Path):
        raise self.error


class _FakePage:
    def __init__(self, page_no: int, markdown: str) -> None:
        self.page_number = page_no
        self.markdown = markdown
        self.source_provider = "test"


@pytest.fixture
def fake_pdf():
    pdf = _WORKSPACE_TMP / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    return pdf


class TestLLMVisionFastFail:
    @pytest.mark.asyncio
    async def test_page_failure_propagates_to_chain(self, fake_pdf):
        """任一页失败 → provider 抛异常，链降级到下一个。"""
        gateway = MagicMock()
        gateway.complete_vision = AsyncMock(side_effect=ConnectionError("disconnected"))

        provider = LLMVisionOCRProvider(name="mimo-vl", gateway=gateway)

        # 需要 mock 渲染 PDF 为 1 页
        with patch(
            "app.domains.document.ocr.providers._render_pdf_pages",
            return_value=["data:image/png;base64,xxx"],
        ):
            with pytest.raises(ConnectionError):
                await provider.extract(fake_pdf)

    @pytest.mark.asyncio
    async def test_chain_falls_back_to_next_provider(self, fake_pdf):
        """mimo 失败 → 链自动降级到 deepseek。"""
        mimo = LLMVisionOCRProvider(name="mimo-vl", gateway=MagicMock())
        mimo.extract = AsyncMock(side_effect=ConnectionError("disconnected"))

        deepseek = LLMVisionOCRProvider(name="deepseek-vl", gateway=MagicMock())
        deepseek.extract = AsyncMock(
            return_value=MagicMock(filename=fake_pdf.name, pages=[])
        )

        chain = OCRFallbackChain([mimo, deepseek])
        doc = await chain.extract(fake_pdf)
        assert doc.provider_used == "deepseek-vl"

    @pytest.mark.asyncio
    async def test_all_providers_failed_raises(self, fake_pdf):
        """所有 provider 失败 → OCRProviderError。"""
        p1 = _FailingProvider("mimo-vl", ConnectionError("disconnected"))
        p2 = _FailingProvider("deepseek-vl", TimeoutError("timeout"))

        chain = OCRFallbackChain([p1, p2])
        with pytest.raises(OCRProviderError) as excinfo:
            await chain.extract(fake_pdf)
        assert "mimo-vl" in str(excinfo.value)
        assert "deepseek-vl" in str(excinfo.value)

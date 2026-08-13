import asyncio
import json
from pathlib import Path

import httpx

from app.domains.document.ocr.paddle_client import PaddleOCRClient
from app.domains.document.ocr.providers import (
    MockOCRProvider,
    OCRFallbackChain,
    OCRProviderError,
)
from app.domains.document.schemas import OcrDocument, OcrPage


def test_paddle_client_parses_layout_jsonl() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(
                200,
                json={"data": {"jobId": "job-1"}},
            )
        if request.url.path.endswith("/ocr/jobs/job-1"):
            return httpx.Response(
                200,
                json={
                    "data": {
                        "state": "done",
                        "resultUrl": {
                            "jsonUrl": "https://example.com/result.jsonl"
                        },
                    }
                },
            )
        if request.url.path.endswith("result.jsonl"):
            line = json.dumps(
                {
                    "result": {
                        "layoutParsingResults": [
                            {
                                "markdown": {
                                    "text": "# page",
                                    "images": {
                                        "img.png": "https://example.com/img.png"
                                    },
                                }
                            }
                        ]
                    }
                },
                ensure_ascii=False,
            )
            return httpx.Response(200, text=line)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    client = PaddleOCRClient(
        base_url="https://example.com/api/v2/ocr/jobs",
        token="secret",
        transport=transport,
        poll_interval_seconds=0,
    )
    pdf_path = (
        Path(__file__).resolve().parents[2]
        / "test"
        / "pdf"
        / "2026北京朝阳高一（上）期末数学（教师版）.pdf"
    )

    document = asyncio.run(client.extract(pdf_path))

    assert document.pages[0].markdown == "# page"
    assert document.pages[0].images[0].url == "https://example.com/img.png"


class FailingOCRProvider:
    name = "failing"

    async def extract(self, file_path: Path) -> OcrDocument:
        raise OCRProviderError("boom")


class PassingOCRProvider:
    name = "passing"

    async def extract(self, file_path: Path) -> OcrDocument:
        return OcrDocument(
            filename=file_path.name,
            pages=[
                OcrPage(page_number=1, markdown="ok", source_provider=self.name)
            ],
        )


def test_ocr_fallback_chain_uses_next_provider() -> None:
    chain = OCRFallbackChain([FailingOCRProvider(), PassingOCRProvider()])

    document = asyncio.run(chain.extract(Path("test.pdf")))

    assert document.provider_used == "passing"
    assert document.pages[0].markdown == "ok"


def test_mock_ocr_provider_returns_deterministic_page() -> None:
    document = asyncio.run(MockOCRProvider().extract(Path("test.pdf")))

    assert document.provider_used == "mock"
    assert "示例题干" in document.pages[0].markdown

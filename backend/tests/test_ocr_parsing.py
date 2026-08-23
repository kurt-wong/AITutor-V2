import asyncio
import json
import tempfile
from pathlib import Path

import pytest
import httpx

from app.domains.document.ocr.paddle_client import PaddleOCRClient
from app.domains.document.ocr.providers import (
    MockOCRProvider,
    OCRFallbackChain,
    OCRProviderError,
)
from app.domains.document.schemas import OcrDocument, OcrPage


def _tmp_pdf() -> Path:
    """创建一个最小的临时 PDF 文件用于测试。"""
    p = Path(tempfile.mktemp(suffix=".pdf"))
    p.write_bytes(b"%PDF-1.4 fake")
    return p


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
                        "extractProgress": {"totalPages": 1, "extractedPages": 1},
                        "resultUrl": {
                            "jsonUrl": "https://example.com/result.jsonl"
                        },
                    }
                },
            )
        if request.url.path.endswith("result.jsonl"):
            line = json.dumps(
                {
                    "page": 1,
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


# ═══════════════════════════════════════════════════════════════════
# C1: extractProgress 校验
# ═══════════════════════════════════════════════════════════════════


def test_paddle_client_rejects_incomplete_extract_progress() -> None:
    """extractProgress.extractedPages < totalPages 时应抛出异常。"""
    from app.domains.document.ocr.paddle_client import PaddleOCRClientError

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(200, json={"data": {"jobId": "job-inc"}})
        if request.url.path.endswith("/ocr/jobs/job-inc"):
            return httpx.Response(
                200,
                json={
                    "data": {
                        "state": "done",
                        "extractProgress": {"totalPages": 10, "extractedPages": 5},
                        "resultUrl": {"jsonUrl": "https://example.com/r.jsonl"},
                    }
                },
            )
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    client = PaddleOCRClient(
        base_url="https://example.com/api/v2/ocr/jobs",
        token="secret",
        transport=transport,
        poll_interval_seconds=0,
    )

    try:
        asyncio.run(client.extract(_tmp_pdf()))
        raise AssertionError("expected PaddleOCRClientError")
    except PaddleOCRClientError as e:
        assert "incomplete" in str(e)
        assert "5/10" in str(e)


def test_paddle_client_accepts_complete_extract_progress() -> None:
    """extractProgress.extractedPages == totalPages 时应正常返回。"""
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(200, json={"data": {"jobId": "job-ok"}})
        if request.url.path.endswith("/ocr/jobs/job-ok"):
            return httpx.Response(
                200,
                json={
                    "data": {
                        "state": "done",
                        "extractProgress": {"totalPages": 3, "extractedPages": 3},
                        "resultUrl": {"jsonUrl": "https://example.com/r.jsonl"},
                    }
                },
            )
        if request.url.path.endswith("r.jsonl"):
            line = json.dumps({"page": 1, "result": {"layoutParsingResults": [{"markdown": {"text": "ok"}}]}})
            return httpx.Response(200, text=line)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    client = PaddleOCRClient(
        base_url="https://example.com/api/v2/ocr/jobs",
        token="secret",
        transport=transport,
        poll_interval_seconds=0,
    )

    doc = asyncio.run(client.extract(_tmp_pdf()))
    assert len(doc.pages) == 1


# ═══════════════════════════════════════════════════════════════════
# C2: JSONL page 字段使用
# ═══════════════════════════════════════════════════════════════════


def test_paddle_client_uses_jsonl_page_number() -> None:
    """JSONL 的 page 字段应被用作 page_number，而非 len(pages)+1。"""
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(200, json={"data": {"jobId": "job-p"}})
        if request.url.path.endswith("/ocr/jobs/job-p"):
            return httpx.Response(
                200,
                json={
                    "data": {
                        "state": "done",
                        "extractProgress": {"totalPages": 1, "extractedPages": 1},
                        "resultUrl": {"jsonUrl": "https://example.com/r.jsonl"},
                    }
                },
            )
        if request.url.path.endswith("r.jsonl"):
            # 两行 JSONL，page 分别是 3 和 7（模拟跳页）
            lines = [
                json.dumps({"page": 3, "result": {"layoutParsingResults": [{"markdown": {"text": "p3"}}]}}),
                json.dumps({"page": 7, "result": {"layoutParsingResults": [{"markdown": {"text": "p7"}}]}}),
            ]
            return httpx.Response(200, text="\n".join(lines))
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    client = PaddleOCRClient(
        base_url="https://example.com/api/v2/ocr/jobs",
        token="secret",
        transport=transport,
        poll_interval_seconds=0,
    )

    doc = asyncio.run(client.extract(_tmp_pdf()))
    assert doc.pages[0].page_number == 3
    assert doc.pages[1].page_number == 7
    assert doc.pages[0].markdown == "p3"
    assert doc.pages[1].markdown == "p7"


def test_paddle_client_falls_back_to_sequence_without_page_field() -> None:
    """JSONL 无 page 字段时（真实 PP API 格式）按 layoutParsingResults 顺序编号，不再报错。"""
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(200, json={"data": {"jobId": "job-np"}})
        if request.url.path.endswith("/ocr/jobs/job-np"):
            return httpx.Response(
                200,
                json={
                    "data": {
                        "state": "done",
                        "extractProgress": {"totalPages": 1, "extractedPages": 1},
                        "resultUrl": {"jsonUrl": "https://example.com/r.jsonl"},
                    }
                },
            )
        if request.url.path.endswith("r.jsonl"):
            # 真实 PP API：JSONL 行缺少顶层 page 字段（logId + result.layoutParsingResults）
            line = json.dumps({"logId": "abc", "result": {"layoutParsingResults": [
                {"markdown": {"text": "no page"}}]}})
            return httpx.Response(200, text=line)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    client = PaddleOCRClient(
        base_url="https://example.com/api/v2/ocr/jobs",
        token="secret",
        transport=transport,
        poll_interval_seconds=0,
    )

    doc = asyncio.run(client.extract(_tmp_pdf()))
    assert len(doc.pages) == 1
    assert doc.pages[0].page_number == 1
    assert doc.pages[0].markdown == "no page"


def test_paddle_client_rejects_non_positive_page() -> None:
    """JSONL page 字段非正整数时应抛出 PaddleOCRClientError。"""
    from app.domains.document.ocr.paddle_client import PaddleOCRClientError

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(200, json={"data": {"jobId": "job-zp"}})
        if request.url.path.endswith("/ocr/jobs/job-zp"):
            return httpx.Response(
                200,
                json={
                    "data": {
                        "state": "done",
                        "extractProgress": {"totalPages": 1, "extractedPages": 1},
                        "resultUrl": {"jsonUrl": "https://example.com/r.jsonl"},
                    }
                },
            )
        if request.url.path.endswith("r.jsonl"):
            line = json.dumps({"page": 0, "result": {"layoutParsingResults": [{"markdown": {"text": "zero page"}}]}})
            return httpx.Response(200, text=line)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    client = PaddleOCRClient(
        base_url="https://example.com/api/v2/ocr/jobs",
        token="secret",
        transport=transport,
        poll_interval_seconds=0,
    )

    with pytest.raises(PaddleOCRClientError, match="page"):
        asyncio.run(client.extract(_tmp_pdf()))


# ═══════════════════════════════════════════════════════════════════
# Fix 2 (CRITICAL): extractProgress 缺少字段必须拒绝
# ═══════════════════════════════════════════════════════════════════


def test_paddle_client_rejects_missing_extract_progress() -> None:
    """state=done 但无 extractProgress → 抛出 PaddleOCRClientError。"""
    from app.domains.document.ocr.paddle_client import PaddleOCRClientError

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(200, json={"data": {"jobId": "job-noprog"}})
        if request.url.path.endswith("/ocr/jobs/job-noprog"):
            return httpx.Response(
                200,
                json={
                    "data": {
                        "state": "done",
                        "resultUrl": {"jsonUrl": "https://example.com/r.jsonl"},
                    }
                },
            )
        # JSONL 需要被 serve（虽然 _poll 会在 parse 之前抛错）
        if "r.jsonl" in str(request.url):
            line = json.dumps({"page": 1, "result": {"layoutParsingResults": [{"markdown": {"text": "ok"}}]}})
            return httpx.Response(200, text=line)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    client = PaddleOCRClient(
        base_url="https://example.com/api/v2/ocr/jobs",
        token="secret",
        transport=transport,
        poll_interval_seconds=0,
    )

    with pytest.raises(PaddleOCRClientError, match="extractProgress"):
        asyncio.run(client.extract(_tmp_pdf()))


def test_paddle_client_rejects_invalid_extract_progress_type() -> None:
    """extractProgress.totalPages 非 int → 抛出 PaddleOCRClientError。"""
    from app.domains.document.ocr.paddle_client import PaddleOCRClientError

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(200, json={"data": {"jobId": "job-badtype"}})
        if request.url.path.endswith("/ocr/jobs/job-badtype"):
            return httpx.Response(
                200,
                json={
                    "data": {
                        "state": "done",
                        "extractProgress": {"totalPages": "abc", "extractedPages": 5},
                        "resultUrl": {"jsonUrl": "https://example.com/r.jsonl"},
                    }
                },
            )
        if "r.jsonl" in str(request.url):
            line = json.dumps({"page": 1, "result": {"layoutParsingResults": [{"markdown": {"text": "ok"}}]}})
            return httpx.Response(200, text=line)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    client = PaddleOCRClient(
        base_url="https://example.com/api/v2/ocr/jobs",
        token="secret",
        transport=transport,
        poll_interval_seconds=0,
    )

    with pytest.raises(PaddleOCRClientError, match="totalPages"):
        asyncio.run(client.extract(_tmp_pdf()))


def test_paddle_client_rejects_bool_extract_progress() -> None:
    """extractProgress 使用 bool 值 → 抛出 PaddleOCRClientError（bool 是 int 子类）。"""
    from app.domains.document.ocr.paddle_client import PaddleOCRClientError

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(200, json={"data": {"jobId": "job-bool"}})
        if request.url.path.endswith("/ocr/jobs/job-bool"):
            return httpx.Response(
                200,
                json={
                    "data": {
                        "state": "done",
                        "extractProgress": {"totalPages": True, "extractedPages": True},
                        "resultUrl": {"jsonUrl": "https://example.com/r.jsonl"},
                    }
                },
            )
        if "r.jsonl" in str(request.url):
            line = json.dumps({"page": 1, "result": {"layoutParsingResults": [{"markdown": {"text": "ok"}}]}})
            return httpx.Response(200, text=line)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    client = PaddleOCRClient(
        base_url="https://example.com/api/v2/ocr/jobs",
        token="secret",
        transport=transport,
        poll_interval_seconds=0,
    )

    with pytest.raises(PaddleOCRClientError, match="totalPages"):
        asyncio.run(client.extract(_tmp_pdf()))


def test_paddle_client_rejects_extracted_gt_total() -> None:
    """extractedPages > totalPages → 抛出 PaddleOCRClientError。"""
    from app.domains.document.ocr.paddle_client import PaddleOCRClientError

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(200, json={"data": {"jobId": "job-gt"}})
        if request.url.path.endswith("/ocr/jobs/job-gt"):
            return httpx.Response(
                200,
                json={
                    "data": {
                        "state": "done",
                        "extractProgress": {"totalPages": 5, "extractedPages": 10},
                        "resultUrl": {"jsonUrl": "https://example.com/r.jsonl"},
                    }
                },
            )
        if "r.jsonl" in str(request.url):
            line = json.dumps({"page": 1, "result": {"layoutParsingResults": [{"markdown": {"text": "ok"}}]}})
            return httpx.Response(200, text=line)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    client = PaddleOCRClient(
        base_url="https://example.com/api/v2/ocr/jobs",
        token="secret",
        transport=transport,
        poll_interval_seconds=0,
    )

    with pytest.raises(PaddleOCRClientError, match="incomplete"):
        asyncio.run(client.extract(_tmp_pdf()))

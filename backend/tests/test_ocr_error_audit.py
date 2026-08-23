"""OCR 错误可审计性测试 — WP2。

覆盖：
  - PaddleOCRClient HTTP 错误必须包含 status 和 body
  - extractProgress 异常必须报告原始字段
  - OCRFallbackChain 失败必须保留每个 provider 的失败明细
  - ocr_smoke 记录合法性（成功有 pages，失败有明确 error）
"""

import asyncio
import json
import sys
import tempfile
from pathlib import Path

import httpx
import pytest

from app.domains.document.ocr.paddle_client import PaddleOCRClient, PaddleOCRClientError
from app.domains.document.ocr.providers import OCRFallbackChain, OCRProviderError
from app.ai.gateway import LLMGateway, LLMGatewayError

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "test" / "scripts"))
import ocr_smoke


def _tmp_pdf() -> Path:
    p = Path(tempfile.mktemp(suffix=".pdf"))
    p.write_bytes(b"%PDF-1.4 fake")
    return p


def test_paddle_client_http_error_includes_status_and_body() -> None:
    """提交阶段 HTTP 400 必须带出 status 和 body，不能只抛通用错误。"""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(
                400,
                text='{"code": "INVALID_ARGUMENT", "message": "bad model"}',
            )
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    client = PaddleOCRClient(
        base_url="https://example.com/api/v2/ocr/jobs",
        token="secret",
        transport=transport,
        poll_interval_seconds=0,
    )
    with pytest.raises(PaddleOCRClientError) as excinfo:
        asyncio.run(client.extract(_tmp_pdf()))
    message = str(excinfo.value)
    assert "HTTP 400" in message, f"错误消息应包含 HTTP 400: {message}"
    assert "INVALID_ARGUMENT" in message, f"错误消息应包含响应体: {message}"


def test_paddle_client_invalid_progress_reports_raw_fields() -> None:
    """extractProgress 缺失/异常时必须报告原始 data 字段，便于复现格式错误。"""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(200, json={"data": {"jobId": "job-1"}})
        if request.url.path.endswith("/job-1"):
            # extractProgress 缺失（模拟"返回格式错误"）
            return httpx.Response(
                200,
                json={"data": {"state": "done", "resultUrl": {"jsonUrl": "https://e.com/r"}}},
            )
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    client = PaddleOCRClient(
        base_url="https://example.com/api/v2/ocr/jobs",
        token="secret",
        transport=transport,
        poll_interval_seconds=0,
    )
    with pytest.raises(PaddleOCRClientError) as excinfo:
        asyncio.run(client.extract(_tmp_pdf()))
    message = str(excinfo.value)
    assert "extractProgress" in message
    assert "raw data=" in message, f"错误消息应包含原始 data 片段: {message}"


def test_paddle_client_incomplete_pages_reports_ratio() -> None:
    """extractedPages != totalPages 时必须报告比例和原始字段。"""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(200, json={"data": {"jobId": "job-1"}})
        if request.url.path.endswith("/job-1"):
            return httpx.Response(
                200,
                json={
                    "data": {
                        "state": "done",
                        "extractProgress": {"totalPages": 5, "extractedPages": 3},
                        "resultUrl": {"jsonUrl": "https://e.com/r"},
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
    with pytest.raises(PaddleOCRClientError) as excinfo:
        asyncio.run(client.extract(_tmp_pdf()))
    message = str(excinfo.value)
    assert "3/5" in message, f"错误消息应包含 3/5: {message}"


def test_ocr_fallback_chain_preserves_provider_failures() -> None:
    """全部 provider 失败时，OCRProviderError 必须保留每个 provider 的失败明细。"""

    class FailingProvider:
        name = "fail_a"

        async def extract(self, file_path):
            raise httpx.HTTPStatusError(
                "provider=fail_a HTTP 401: unauthorized",
                request=httpx.Request("POST", "https://example.com"),
                response=httpx.Response(401, text="unauthorized"),
            )

    class FailingProvider2:
        name = "fail_b"

        async def extract(self, file_path):
            raise ValueError("boom")

    chain = OCRFallbackChain([FailingProvider(), FailingProvider2()])
    with pytest.raises(OCRProviderError) as excinfo:
        asyncio.run(chain.extract(_tmp_pdf()))

    err = excinfo.value
    assert err.failures, "OCRProviderError.failures 不应为空"
    names = [name for name, _ in err.failures]
    assert names == ["fail_a", "fail_b"], f"应保留全部 provider 失败: {names}"
    msg_a = dict(err.failures)["fail_a"]
    assert "401" in msg_a, f"fail_a 的错误应包含 status: {msg_a}"
    assert "unauthorized" in msg_a, f"fail_a 的错误应包含 body: {msg_a}"
    assert "boom" in dict(err.failures)["fail_b"]
    assert "fail_a" in str(err) and "fail_b" in str(err)


def test_ocr_smoke_requires_pages_or_explicit_error() -> None:
    """ocr_smoke 记录：成功必须有 pages/provider_used/source_provider，失败必须有 error。"""
    # 合法成功记录
    ok_record = {
        "status": "ok", "provider": "paddleocr", "pages": 5,
        "provider_used": "paddleocr", "source_provider": ["PP-StructureV3"],
    }
    assert ocr_smoke.validate_smoke_record(ok_record) == []

    # 成功但缺 pages → 错误
    assert any("pages" in e for e in ocr_smoke.validate_smoke_record(
        {"status": "ok", "provider": "paddleocr", "pages": None,
         "provider_used": "paddleocr", "source_provider": ["x"]}
    ))
    # 成功但缺 provider_used → 错误
    assert any("provider_used" in e for e in ocr_smoke.validate_smoke_record(
        {"status": "ok", "provider": "paddleocr", "pages": 1,
         "provider_used": None, "source_provider": ["x"]}
    ))

    # 合法失败记录（有 http_status）
    fail_record = {"status": "failed", "provider": "paddleocr",
                   "http_status": 400, "raw_body": "bad", "error": "HTTP 400: bad"}
    assert ocr_smoke.validate_smoke_record(fail_record) == []

    # 失败但无 error 且无 status/body → 错误
    bad_fail = {"status": "failed", "provider": "paddleocr",
                "http_status": None, "raw_body": None, "error": None}
    assert ocr_smoke.validate_smoke_record(bad_fail) != []

    # 未知 status → 错误
    assert ocr_smoke.validate_smoke_record({"status": "weird", "provider": "x"}) != []


def test_ocr_smoke_extracts_http_info_from_httpx_error() -> None:
    """summarize_failure 必须从 httpx.HTTPStatusError 提取 status 和 body。"""
    exc = httpx.HTTPStatusError(
        "Client error '400 Bad Request'",
        request=httpx.Request("POST", "https://example.com"),
        response=httpx.Response(400, text='{"error": "bad request body"}'),
    )
    record = ocr_smoke.summarize_failure("mimo", exc)
    assert record["status"] == "failed"
    assert record["http_status"] == 400
    assert record["raw_body"] == '{"error": "bad request body"}'
    assert record["error"]


def test_ocr_smoke_extracts_raw_from_paddle_format_error() -> None:
    """格式类错误（HTTP 200 但 JSONL 契约不符）必须能从 raw= 片段提取 raw_body。"""
    exc = PaddleOCRClientError(
        "JSONL line 0 missing 'page' field; raw='{\"logId\": \"abc\"}'"
    )
    info = ocr_smoke.extract_http_info(exc)
    assert info["http_status"] is None
    assert info["raw_body"] == "'{\"logId\": \"abc\"}'", f"应提取 raw 片段: {info['raw_body']}"
    record = ocr_smoke.summarize_failure("paddleocr", exc)
    # 有 raw_body 即可通过校验（不需要 http_status，因为 HTTP 本身成功）
    assert ocr_smoke.validate_smoke_record(record) == []


def test_ocr_smoke_summarize_success() -> None:
    """summarize_success 必须记录 pages / provider_used / source_provider。"""
    from app.domains.document.schemas import OcrDocument, OcrPage

    doc = OcrDocument(
        filename="f.pdf",
        pages=[
            OcrPage(page_number=1, markdown="m", source_provider="mimo"),
            OcrPage(page_number=2, markdown="m", source_provider="mimo"),
        ],
        provider_used="mimo",
    )
    record = ocr_smoke.summarize_success("mimo", doc)
    assert record["status"] == "ok"
    assert record["pages"] == 2
    assert record["provider_used"] == "mimo"
    assert record["source_provider"] == ["mimo"]


def test_gateway_vision_failure_includes_provider_details() -> None:
    """LLMGateway.complete_vision 全部失败时，错误消息必须包含 provider 名和失败明细。"""

    class FailingVisionProvider:
        name = "mimo"

        async def complete_vision(self, prompt, image_data_url, *, temperature=0.2):
            raise httpx.HTTPStatusError(
                "provider=mimo HTTP 400: bad request body",
                request=httpx.Request("POST", "https://example.com"),
                response=httpx.Response(400, text="bad request body"),
            )

    gateway = LLMGateway(mode="live", providers=[FailingVisionProvider()])
    with pytest.raises(LLMGatewayError) as excinfo:
        asyncio.run(gateway.complete_vision("p", "data:image/png;base64,x"))
    message = str(excinfo.value)
    assert "mimo" in message, f"错误消息应包含 provider 名: {message}"
    assert "400" in message, f"错误消息应包含 HTTP 状态: {message}"
    assert "bad request body" in message, f"错误消息应包含 body: {message}"


def _paddle_client_with_jsonl(jsonl_text: str) -> PaddleOCRClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(200, json={"data": {"jobId": "job-jsonl"}})
        if request.url.path.endswith("/job-jsonl"):
            return httpx.Response(
                200,
                json={
                    "data": {
                        "state": "done",
                        "extractProgress": {"totalPages": 9, "extractedPages": 9},
                        "resultUrl": {"jsonUrl": "https://example.com/r.jsonl"},
                    }
                },
            )
        if request.url.path.endswith("r.jsonl"):
            return httpx.Response(200, text=jsonl_text)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    return PaddleOCRClient(
        base_url="https://example.com/api/v2/ocr/jobs",
        token="secret",
        transport=transport,
        poll_interval_seconds=0,
    )


def test_paddle_client_parses_jsonl_without_page_field() -> None:
    """真实 PP API 格式（无顶层 page 字段）必须按 layoutParsingResults 顺序编号。"""
    lines = "\n".join([
        json.dumps({"logId": "a", "result": {"layoutParsingResults": [
            {"markdown": {"text": "page one"}}]}}),
        json.dumps({"logId": "b", "result": {"layoutParsingResults": [
            {"markdown": {"text": "page two"}}]}}),
    ])
    client = _paddle_client_with_jsonl(lines)
    doc = asyncio.run(client.extract(_tmp_pdf()))
    assert len(doc.pages) == 2
    assert [p.page_number for p in doc.pages] == [1, 2]
    assert doc.pages[0].markdown == "page one"
    assert doc.pages[1].markdown == "page two"


def test_paddle_client_parses_multi_layout_same_line() -> None:
    """一行含多个 layoutParsingResults 元素时，页码按元素递增（每元素一页）。"""
    line = json.dumps({"logId": "a", "result": {"layoutParsingResults": [
        {"markdown": {"text": "p1"}},
        {"markdown": {"text": "p2"}},
        {"markdown": {"text": "p3"}},
    ]}})
    client = _paddle_client_with_jsonl(line)
    doc = asyncio.run(client.extract(_tmp_pdf()))
    assert len(doc.pages) == 3
    assert [p.page_number for p in doc.pages] == [1, 2, 3]


def test_paddle_client_explicit_page_still_works() -> None:
    """显式 page 字段优先于计数器（向后兼容）。"""
    line = json.dumps({"page": 7, "result": {"layoutParsingResults": [
        {"markdown": {"text": "p7"}}]}})
    client = _paddle_client_with_jsonl(line)
    doc = asyncio.run(client.extract(_tmp_pdf()))
    assert doc.pages[0].page_number == 7

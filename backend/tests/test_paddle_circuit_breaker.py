"""P0-D 测试：paddle 队列满（10010）熔断 + 快速降级。

背景：paddle AIStudio API 服务端"任务提交队列已满"（HTTP 400 code 10010）
是共享队列状态，重试 6 次（155s）大概率仍满。熔断机制：
- 10010 连续 2 次 → 熔断打开 300s
- 熔断打开时 extract 直接抛异常，让 OCRFallbackChain 立即降级 VL
- 熔断到期自动恢复
"""

import asyncio
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.domains.document.ocr.paddle_client import (
    PaddleOCRClient,
    PaddleOCRClientError,
    _circuit_breaker,
    _circuit_open,
    _trip_circuit,
    _is_queue_full_error,
    _CIRCUIT_OPEN_SECONDS,
)

_WORKSPACE_TMP = Path(__file__).resolve().parents[2] / "tmp" / "pytest_circuit"
_WORKSPACE_TMP.mkdir(parents=True, exist_ok=True)


@pytest.fixture(autouse=True)
def reset_circuit():
    """每个测试前重置熔断状态。"""
    _circuit_breaker["open_until"] = 0.0
    yield
    _circuit_breaker["open_until"] = 0.0


def _fake_pdf(name: str = "test.pdf") -> Path:
    """创建临时 PDF 文件（工作区 tmp，避免沙箱 temp 权限问题）。"""
    pdf = _WORKSPACE_TMP / name
    pdf.write_bytes(b"%PDF-1.4 fake pdf content")
    return pdf


class TestCircuitBreakerState:
    def test_circuit_closed_initially(self):
        assert not _circuit_open()

    def test_trip_opens_circuit(self):
        _trip_circuit()
        assert _circuit_open()

    def test_circuit_auto_recovers_after_timeout(self):
        _trip_circuit()
        assert _circuit_open()
        # 模拟熔断到期
        _circuit_breaker["open_until"] = time.monotonic() - 1
        assert not _circuit_open()

    def test_is_queue_full_error_detects_10010(self):
        resp = MagicMock()
        resp.status_code = 400
        resp.text = '{"code":10010,"msg":"queue full"}'
        assert _is_queue_full_error(resp)

    def test_is_queue_full_error_rejects_other_400(self):
        resp = MagicMock()
        resp.status_code = 400
        resp.text = '{"code":422,"msg":"invalid param"}'
        assert not _is_queue_full_error(resp)

    def test_is_queue_full_error_rejects_429(self):
        resp = MagicMock()
        resp.status_code = 429
        resp.text = "too many requests"
        assert not _is_queue_full_error(resp)


class TestExtractCircuitBreaker:
    @pytest.mark.asyncio
    async def test_extract_skips_when_circuit_open(self):
        """熔断打开时，extract 直接抛异常，不发起请求。"""
        client = PaddleOCRClient(
            base_url="https://example.com/api",
            token="test-token",
        )
        _trip_circuit()
        file_path = _fake_pdf()
        with pytest.raises(PaddleOCRClientError, match="circuit breaker"):
            await client.extract(file_path)

    @pytest.mark.asyncio
    async def test_two_queue_full_errors_trip_circuit(self):
        """连续 2 次 10010 → 触发熔断。"""
        client = PaddleOCRClient(
            base_url="https://example.com/api",
            token="test-token",
            submit_max_retries=2,
            submit_retry_delay=0.01,
        )

        # 模拟 10010 响应
        async def fake_post(*args, **kwargs):
            return httpx.Response(400, text='{"code":10010,"msg":"queue full"}')

        file_path = _fake_pdf()
        with patch("httpx.AsyncClient.post", new=fake_post):
            with pytest.raises(PaddleOCRClientError, match="10010"):
                await client.extract(file_path)

        # 熔断应已打开
        assert _circuit_open()

    @pytest.mark.asyncio
    async def test_success_resets_streak(self):
        """成功后连续计数清零，熔断不触发。"""
        client = PaddleOCRClient(
            base_url="https://example.com/api",
            token="test-token",
            submit_max_retries=2,
            submit_retry_delay=0.01,
        )

        async def fake_post(*args, **kwargs):
            return httpx.Response(200, json={"data": {"jobId": "job-1"}})

        file_path = _fake_pdf()
        with patch("httpx.AsyncClient.post", new=fake_post):
            # 需要 mock 后续 poll 和 jsonl 下载
            mock_doc = MagicMock()
            with patch.object(client, "_poll", new=AsyncMock(return_value={
                "resultUrl": {"jsonUrl": "https://example.com/result.jsonl"}
            })), patch("httpx.AsyncClient.get", new=AsyncMock(return_value=httpx.Response(200, text=""))), \
                patch.object(client, "_parse_jsonl", return_value=mock_doc):
                await client.extract(file_path)

        assert not _circuit_open()

"""P7/P10 修复测试：LLM 请求总超时兜底（挂死请求强制取消）。

worker 内 LLM 请求挂死（httpx 空闲超时失效）时，asyncio.wait_for 总超时
应取消请求并抛 TimeoutError → 重试 → 全部失败时抛错（不无限等待）。
"""
from __future__ import annotations

import asyncio

import httpx
import pytest

from app.ai.providers.http import HTTPLLMProvider


class _HungTransport(httpx.AsyncBaseTransport):
    """模拟挂死：接受连接后永不返回（不响应也不关闭）。"""

    async def handle_async_request(self, request):
        await asyncio.Event().wait()  # 永不返回


def _make_provider(total_timeout: float = 0.2, max_retries: int = 1) -> HTTPLLMProvider:
    return HTTPLLMProvider(
        name="test-hung",
        base_url="https://example.invalid",
        api_key="k",
        model="test-model",
        timeout_seconds=60.0,
        total_timeout_seconds=total_timeout,
        max_retries=max_retries,
        retry_base_delay=0.01,
    )


@pytest.mark.asyncio
async def test_hung_request_cancelled_by_total_timeout() -> None:
    """挂死请求在总超时后被取消（抛错而非无限等待）。"""
    provider = _make_provider(total_timeout=0.2, max_retries=0)
    client = httpx.AsyncClient(transport=_HungTransport())
    # 注入挂死 transport（HTTPLLMProvider 内部用 httpx.AsyncClient(timeout=...)，
    # 此处 monkeypatch 其 post 为挂死协程最直接）。
    import app.ai.providers.http as http_mod

    async def hung_post(*args, **kwargs):
        await asyncio.Event().wait()

    original = httpx.AsyncClient.post
    httpx.AsyncClient.post = hung_post  # type: ignore[assignment]
    try:
        t0 = asyncio.get_event_loop().time()
        with pytest.raises(TimeoutError):
            await provider.complete("hello")
        elapsed = asyncio.get_event_loop().time() - t0
        # 2026-08-27：断言从 2.0s 放宽到 5.0s——httpx.AsyncClient 构造在
        # 沙箱/高负载下实测耗时 0.9-1.9s（wait_for 本身 0.2s），旧上限在
        # 负载下确定性超限（全量 684 测试时 elapsed=2.19s）。功能断言
        # （TimeoutError 抛出）不变，这里只是总耗时性能护栏。
        assert elapsed < 5.0, f"应在总超时附近返回，实际 {elapsed:.2f}s"
    finally:
        httpx.AsyncClient.post = original  # type: ignore[assignment]
        await client.aclose()


@pytest.mark.asyncio
async def test_hung_request_retries_then_raises() -> None:
    """挂死请求重试（max_retries 次）后最终抛错。"""
    provider = _make_provider(total_timeout=0.2, max_retries=2)
    import app.ai.providers.http as http_mod

    calls = {"n": 0}

    async def hung_post(*args, **kwargs):
        calls["n"] += 1
        await asyncio.Event().wait()

    original = httpx.AsyncClient.post
    httpx.AsyncClient.post = hung_post  # type: ignore[assignment]
    try:
        with pytest.raises(TimeoutError):
            await provider.complete("hello")
        assert calls["n"] == 3, f"应重试 3 次（max_retries=2），实际 {calls['n']}"
    finally:
        httpx.AsyncClient.post = original  # type: ignore[assignment]


@pytest.mark.asyncio
async def test_normal_request_untouched() -> None:
    """正常（快速）请求不受总超时影响。"""
    provider = _make_provider(total_timeout=10.0, max_retries=0)
    import app.ai.providers.http as http_mod

    async def ok_post(*args, **kwargs):
        class _Resp:
            status_code = 200
            text = "{}"

            def json(self):
                return {"choices": [{"message": {"content": "ok", "reasoning_content": ""}}]}

        return _Resp()

    original = httpx.AsyncClient.post
    httpx.AsyncClient.post = ok_post  # type: ignore[assignment]
    try:
        text = await provider.complete("hello")
        assert text == "ok"
    finally:
        httpx.AsyncClient.post = original  # type: ignore[assignment]

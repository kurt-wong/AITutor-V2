import asyncio
import logging
from typing import Any

import httpx

from app.ai.providers.base import LLMProvider

logger = logging.getLogger(__name__)


def extract_completion_text(data: dict[str, Any]) -> str:
    """Return message text from OpenAI-compatible completion responses."""
    choices = data.get("choices") or []
    if not choices:
        raise ValueError("LLM response has no choices")

    choice = choices[0]
    if not isinstance(choice, dict):
        raise ValueError("LLM response choice is not an object")

    message = choice.get("message") or {}
    if not isinstance(message, dict):
        raise ValueError("LLM response message is not an object")

    content = message.get("content")
    if content is None:
        content = message.get("text")
    if content is None:
        content = message.get("output_text")
    if content is None:
        content = choice.get("text")
    if content is None and isinstance(data.get("output"), dict):
        content = data["output"].get("text") or data["output"].get("content")

    if isinstance(content, str):
        text = content.strip()
        if text:
            return text
        raise ValueError("LLM response message content is empty")

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                part = item.get("text") or item.get("content") or item.get("value")
                if part is not None:
                    parts.append(str(part))
        text = "\n".join(parts).strip()
        if text:
            return text

    if isinstance(content, dict):
        part = content.get("text") or content.get("content") or content.get("value")
        if part is not None:
            text = str(part).strip()
            if text:
                return text

    raise ValueError("LLM response message content is empty or unsupported")


class HTTPLLMProvider(LLMProvider):
    def __init__(
        self,
        *,
        name: str,
        base_url: str,
        api_key: str | None,
        model: str,
        timeout_seconds: float = 60.0,
        total_timeout_seconds: float | None = None,
        response_format: dict[str, str] | None = None,
        max_tokens: int | None = None,
        max_completion_tokens: int | None = None,
        max_retries: int = 2,
        retry_base_delay: float = 1.0,
    ) -> None:
        self.name = name
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        # 2026-08-25 P7/P10 修复：httpx timeout 是"无数据活动"空闲超时——
        # deepseek 流式响应持续有数据时总时长可远超 timeout_seconds（实测
        # 最长 339s），挂死（连接挂起无数据且不关闭）时空闲超时可能失效，
        # 请求无限等待。此处加 asyncio.wait_for 总时长兜底：
        #   max(2×空闲超时, 600s)——容纳正常 reasoning 响应（~6min），
        #   挂死请求 10 分钟内强制取消 → TimeoutError → 走重试/失败路径。
        self._total_timeout = (
            total_timeout_seconds
            if total_timeout_seconds is not None
            else max(timeout_seconds * 2, 600.0)
        )
        self.response_format = response_format
        self.max_tokens = max_tokens
        self.max_completion_tokens = max_completion_tokens
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay

    async def complete(self, prompt: str, *, temperature: float = 0.2) -> str:
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
        if self.response_format:
            payload["response_format"] = self.response_format
        if self.max_tokens:
            payload["max_tokens"] = self.max_tokens
        if self.max_completion_tokens:
            payload["max_completion_tokens"] = self.max_completion_tokens
        logger.info(
            "LLM request provider=%s model=%s max_tokens=%s max_completion_tokens=%s prompt_len=%d",
            self.name, self.model, self.max_tokens, self.max_completion_tokens, len(prompt),
        )
        return await self._post_completion(url, payload=payload)

    async def complete_vision(
        self,
        prompt: str,
        image_data_url: str,
        *,
        temperature: float = 0.2,
    ) -> str:
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": image_data_url},
                        },
                    ],
                }
            ],
            "temperature": temperature,
        }
        return await self._post_completion(url, payload=payload)

    async def _post_completion(self, url: str, *, payload: dict[str, Any]) -> str:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    # P7/P10 修复：总时长兜底（httpx 空闲超时对"挂起无数据"
                    # 可能失效）。超时抛 asyncio.TimeoutError（继承 OSError，
                    # 已被下方 except 覆盖）→ 重试 → 全失败标记。
                    response = await asyncio.wait_for(
                        client.post(url, json=payload, headers=headers),
                        timeout=self._total_timeout,
                    )
                    if response.status_code >= 400:
                        # 必须带出 status 和 body，不能只抛 raise_for_status() 的通用错误
                        # （否则 LLM/OCR 400 失败原因不可复现）
                        body_preview = response.text[:300]
                        raise httpx.HTTPStatusError(
                            f"provider={self.name} HTTP {response.status_code}: {body_preview}",
                            request=response.request,
                            response=response,
                        )
                    data = response.json()
                    if not isinstance(data, dict):
                        raise ValueError("LLM response is not a JSON object")
                    choices = data.get("choices") or []
                    first_choice = choices[0] if choices else None
                    finish_reason = (
                        first_choice.get("finish_reason")
                        if isinstance(first_choice, dict)
                        else None
                    )
                    usage = data.get("usage") or {}
                    completion_tokens = (
                        usage.get("completion_tokens")
                        if isinstance(usage, dict)
                        else None
                    )
                    reasoning_tokens = (
                        (usage.get("completion_tokens_details") or {}).get(
                            "reasoning_tokens"
                        )
                        if isinstance(usage, dict)
                        else None
                    )
                    logger.info(
                        "LLM response provider=%s finish_reason=%s "
                        "completion_tokens=%s reasoning_tokens=%s",
                        self.name,
                        finish_reason,
                        completion_tokens,
                        reasoning_tokens,
                    )
                    return extract_completion_text(data)
            except (httpx.HTTPStatusError, httpx.RequestError, ValueError, OSError) as e:
                last_error = e
                if attempt < self.max_retries:
                    delay = self.retry_base_delay * (2 ** attempt)
                    logger.warning(
                        "provider=%s attempt=%d/%d failed: %s, retrying in %.1fs",
                        self.name, attempt + 1, self.max_retries + 1, e, delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "provider=%s all %d attempts failed: %s",
                        self.name, self.max_retries + 1, e,
                    )
        raise last_error  # type: ignore[misc]

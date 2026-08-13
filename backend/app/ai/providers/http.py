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
        response_format: dict[str, str] | None = None,
        max_retries: int = 2,
        retry_base_delay: float = 1.0,
    ) -> None:
        self.name = name
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.response_format = response_format
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
                    response = await client.post(url, json=payload, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    if not isinstance(data, dict):
                        raise ValueError("LLM response is not a JSON object")
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

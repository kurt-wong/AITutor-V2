import asyncio

import pytest

from app.ai.gateway import LLMGateway, LLMGatewayError


class FailingProvider:
    name = "failing"

    async def complete(self, prompt: str, *, temperature: float = 0.2) -> str:
        raise RuntimeError("provider failed")


class PassingProvider:
    name = "passing"

    async def complete(self, prompt: str, *, temperature: float = 0.2) -> str:
        return "ok"


def test_mock_gateway_returns_mock_response() -> None:
    gateway = LLMGateway(mode="mock")
    text = asyncio.run(gateway.complete("hello"))
    assert text == "MOCK_LLM_RESPONSE"


def test_gateway_falls_back_to_next_provider() -> None:
    gateway = LLMGateway(
        mode="live",
        providers=[FailingProvider(), PassingProvider()],
    )
    text = asyncio.run(gateway.complete("hello"))
    assert text == "ok"


def test_gateway_raises_when_all_providers_fail() -> None:
    gateway = LLMGateway(
        mode="live",
        providers=[FailingProvider()],
    )
    with pytest.raises(LLMGatewayError):
        asyncio.run(gateway.complete("hello"))


class VisionProvider:
    name = "vision"

    async def complete(self, prompt: str, *, temperature: float = 0.2) -> str:
        raise RuntimeError("text mode not supported")

    async def complete_vision(
        self,
        prompt: str,
        image_data_url: str,
        *,
        temperature: float = 0.2,
    ) -> str:
        return "vision-ok"


def test_gateway_vision_uses_vision_capable_provider() -> None:
    gateway = LLMGateway(
        mode="live",
        providers=[VisionProvider()],
    )
    text = asyncio.run(
        gateway.complete_vision("describe", "data:image/png;base64,AAAA")
    )
    assert text == "vision-ok"

import logging
import time

from app.ai.providers import HTTPLLMProvider, LLMProvider, MockLLMProvider
from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMGatewayError(RuntimeError):
    pass


class LLMGateway:
    def __init__(
        self,
        *,
        mode: str,
        providers: list[LLMProvider] | None = None,
    ) -> None:
        self.mode = mode
        self.providers = providers or []

    async def complete(self, prompt: str, *, temperature: float = 0.2) -> str:
        if self.mode == "mock":
            provider = MockLLMProvider()
            return await provider.complete(prompt, temperature=temperature)

        if not self.providers:
            raise LLMGatewayError("no LLM providers configured")

        last_error: Exception | None = None
        for provider in self.providers:
            started_at = time.perf_counter()
            try:
                text = await provider.complete(prompt, temperature=temperature)
                latency_ms = int((time.perf_counter() - started_at) * 1000)
                logger.info(
                    "llm_gateway provider=%s latency_ms=%d",
                    provider.name,
                    latency_ms,
                )
                return text
            except Exception as exc:
                last_error = exc
                logger.warning("llm_gateway provider=%s failed", provider.name)

        raise LLMGatewayError("all LLM providers failed") from last_error

    async def complete_vision(
        self,
        prompt: str,
        image_data_url: str,
        *,
        temperature: float = 0.2,
    ) -> str:
        if self.mode == "mock":
            provider = MockLLMProvider()
            return await provider.complete_vision(
                prompt,
                image_data_url,
                temperature=temperature,
            )

        if not self.providers:
            raise LLMGatewayError("no LLM vision providers configured")

        last_error: Exception | None = None
        for provider in self.providers:
            complete_vision = getattr(provider, "complete_vision", None)
            if complete_vision is None:
                continue
            started_at = time.perf_counter()
            try:
                text = await complete_vision(
                    prompt,
                    image_data_url,
                    temperature=temperature,
                )
                latency_ms = int((time.perf_counter() - started_at) * 1000)
                logger.info(
                    "llm_gateway vision_provider=%s latency_ms=%d",
                    provider.name,
                    latency_ms,
                )
                return text
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "llm_gateway vision_provider=%s failed",
                    provider.name,
                )

        raise LLMGatewayError("all LLM vision providers failed") from last_error


def build_gateway() -> LLMGateway:
    providers: list[LLMProvider] = []
    if (
        settings.deepseek_api_key
        and settings.deepseek_base_url
        and settings.deepseek_model
    ):
        providers.append(
            HTTPLLMProvider(
                name="deepseek",
                base_url=settings.deepseek_base_url,
                api_key=settings.deepseek_api_key,
                model=settings.deepseek_model,
                timeout_seconds=settings.llm_request_timeout_seconds,
            )
        )
    if settings.mimo_api_key and settings.mimo_base_url and settings.mimo_model:
        providers.append(
            HTTPLLMProvider(
                name="mimo",
                base_url=settings.mimo_base_url,
                api_key=settings.mimo_api_key,
                model=settings.mimo_model,
                timeout_seconds=settings.llm_request_timeout_seconds,
                response_format={"type": "json_object"},
            )
        )
    if settings.ollama_base_url and settings.ollama_model:
        providers.append(
            HTTPLLMProvider(
                name="ollama",
                base_url=settings.ollama_base_url,
                api_key=None,
                model=settings.ollama_model,
                timeout_seconds=settings.llm_request_timeout_seconds,
            )
        )
    return LLMGateway(mode=settings.llm_gateway_mode, providers=providers)


llm_gateway = build_gateway()


def get_llm_gateway() -> LLMGateway:
    return llm_gateway

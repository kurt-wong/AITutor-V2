import asyncio
import logging
import time
from datetime import datetime

from app.ai.providers import HTTPLLMProvider, LLMProvider, MockLLMProvider
from app.core.config import settings

logger = logging.getLogger(__name__)

# mimo-v2.5-pro 使用时间段：每天 9:00-12:00, 14:00-18:00
_MIMO_WINDOWS = [(9, 12), (14, 18)]
_MIMO_ENABLED = True


def _is_mimo_window() -> bool:
    """当前时间是否在 mimo-v2.5-pro 使用窗口内。"""
    if not _MIMO_ENABLED:
        return False
    hour = datetime.now().hour
    return any(start <= hour < end for start, end in _MIMO_WINDOWS)


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
        """调用 LLM，支持重试和回退。

        策略：
        1. 每个 provider 最多尝试 2 次（第一次失败后等 5 秒再试一次）
        2. 同一个 provider 连续失败 2 次后，切换到下一个 provider
        3. 所有 provider 都失败后，抛出 LLMGatewayError
        """
        if self.mode == "mock":
            provider = MockLLMProvider()
            return await provider.complete(prompt, temperature=temperature)

        if not self.providers:
            raise LLMGatewayError("no LLM providers configured")

        failures: list[str] = []
        last_error: Exception | None = None

        for provider in self.providers:
            # 每个 provider 最多尝试 2 次
            for attempt in range(2):
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
                    latency_ms = int((time.perf_counter() - started_at) * 1000)
                    failures.append(f"{provider.name} attempt {attempt+1}: {exc}")
                    last_error = exc
                    logger.warning(
                        "llm_gateway provider=%s attempt %d/2 failed (%dms): %s",
                        provider.name, attempt + 1, latency_ms, exc,
                    )
                    if attempt == 0:
                        # 第一次失败，等 5 秒后重试
                        logger.info("llm_gateway retrying %s in 5s...", provider.name)
                        await asyncio.sleep(5)

            # 连续 2 次失败，切换到下一个 provider
            logger.warning(
                "llm_gateway provider=%s failed 2 times, switching to next",
                provider.name,
            )

        detail = "; ".join(failures)
        raise LLMGatewayError(
            f"all LLM providers failed ({detail or 'none'})"
        ) from last_error

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

        failures: list[str] = []
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
                failures.append(f"{provider.name}: {exc}")
                last_error = exc
                logger.warning(
                    "llm_gateway vision_provider=%s failed: %s",
                    provider.name, exc,
                )

        detail = "; ".join(failures)
        raise LLMGatewayError(
            f"all LLM vision providers failed ({detail or 'none'})"
        ) from last_error


def build_gateway() -> LLMGateway:
    providers: list[LLMProvider] = []

    # 构建 deepseek 和 mimo provider
    deepseek_provider = None
    mimo_provider = None
    mimo_vl_provider = None
    deepseek_vl_provider = None

    if (
        settings.deepseek_api_key
        and settings.deepseek_base_url
        and settings.deepseek_model
    ):
        deepseek_provider = HTTPLLMProvider(
            name="deepseek",
            base_url=settings.deepseek_base_url,
            api_key=settings.deepseek_api_key,
            model=settings.deepseek_model,
            timeout_seconds=settings.llm_request_timeout_seconds,
        )

    if (
        settings.deepseek_api_key
        and settings.deepseek_base_url
        and settings.deepseek_vl_model
    ):
        deepseek_vl_provider = HTTPLLMProvider(
            name="deepseek-vl",
            base_url=settings.deepseek_base_url,
            api_key=settings.deepseek_api_key,
            model=settings.deepseek_vl_model,
            timeout_seconds=settings.llm_request_timeout_seconds,
        )

    if settings.mimo_api_key and settings.mimo_base_url and settings.mimo_model:
        mimo_provider = HTTPLLMProvider(
            name="mimo",
            base_url=settings.mimo_base_url,
            api_key=settings.mimo_api_key,
            model=settings.mimo_model,
            timeout_seconds=settings.llm_request_timeout_seconds,
            response_format={"type": "json_object"},
            max_completion_tokens=131072,
        )

    # mimo-v2.5 多模态，用于 VL 任务
    if settings.mimo_api_key and settings.mimo_base_url and settings.mimo_vl_model:
        mimo_vl_provider = HTTPLLMProvider(
            name="mimo-vl",
            base_url=settings.mimo_base_url,
            api_key=settings.mimo_api_key,
            model=settings.mimo_vl_model,
            timeout_seconds=settings.llm_request_timeout_seconds,
            response_format={"type": "json_object"},
        )

    # 时间段切换：mimo 窗口内 mimo 优先，否则 deepseek 优先
    if _is_mimo_window():
        if mimo_provider:
            providers.append(mimo_provider)
            logger.info("LLM: mimo-v2.5-pro (time window)")
        if deepseek_provider:
            providers.append(deepseek_provider)
    else:
        if deepseek_provider:
            providers.append(deepseek_provider)
        if mimo_provider:
            providers.append(mimo_provider)
            logger.info("LLM: mimo-v2.5-pro (fallback)")

    # VL provider：mimo-vl 优先，deepseek-vl 兜底
    if mimo_vl_provider:
        providers.append(mimo_vl_provider)
    if deepseek_vl_provider:
        providers.append(deepseek_vl_provider)

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

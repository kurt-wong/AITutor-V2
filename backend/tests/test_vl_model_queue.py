"""
Tests for VL model queue wrapping in build_ocr_chain().

Verifies that:
1. VL models (containing "VL") use QueuedPaddleOCRProvider with PaddleOCRQueue
2. Non-VL models use plain PaddleOCRClient
3. Queue limits concurrency to 1 for VL models
"""

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.domains.document.ocr.paddle_client import PaddleOCRClient, PaddleOCRQueue
from app.domains.document.ocr.providers import (
    LLMVisionOCRProvider,
    OCRFallbackChain,
    QueuedPaddleOCRProvider,
    build_ocr_chain,
)
from app.domains.document.schemas import OcrDocument, OcrPage


class _FakePaddleClient:
    """记录并发度的假 PaddleOCR client。"""

    def __init__(self) -> None:
        self.active = 0
        self.max_active = 0
        self.calls: list[tuple[str, str | None]] = []

    async def extract(
        self,
        file_path: Path,
        *,
        model: str | None = None,
    ) -> OcrDocument:
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        await asyncio.sleep(0)
        self.active -= 1
        self.calls.append((file_path.name, model))
        return OcrDocument(
            filename=file_path.name,
            pages=[OcrPage(page_number=1, markdown="ok", source_provider="paddleocr")],
        )


class _FlakyPaddleClient(_FakePaddleClient):
    """第一次 extract 失败、后续成功的假 client。"""

    def __init__(self) -> None:
        super().__init__()
        self.fail_next = True

    async def extract(
        self,
        file_path: Path,
        *,
        model: str | None = None,
    ) -> OcrDocument:
        if self.fail_next:
            self.fail_next = False
            raise RuntimeError("boom")
        return await super().extract(file_path, model=model)


class TestQueuedPaddleOCRProvider:
    """Tests for QueuedPaddleOCRProvider adapter."""

    def test_queued_provider_implements_ocr_provider_protocol(self):
        """QueuedPaddleOCRProvider should have extract() method matching OCRProvider protocol."""
        client = MagicMock(spec=PaddleOCRClient)
        client.name = "paddleocr"
        client.model = "PaddleOCR-VL-1.6"

        provider = QueuedPaddleOCRProvider(client, max_concurrent=1)

        # Should have name and extract method
        assert hasattr(provider, "name")
        assert hasattr(provider, "extract")
        assert callable(provider.extract)

    def test_queued_provider_uses_queue_submit(self):
        """QueuedPaddleOCRProvider.extract() should delegate to queue.submit()."""
        mock_queue = MagicMock(spec=PaddleOCRQueue)
        expected_doc = OcrDocument(
            filename="test.pdf",
            pages=[OcrPage(page_number=1, markdown="test", source_provider="paddleocr")],
        )
        mock_queue.submit.return_value = expected_doc

        client = MagicMock(spec=PaddleOCRClient)
        client.name = "paddleocr"
        client.model = "PaddleOCR-VL-1.6"

        provider = QueuedPaddleOCRProvider(client, max_concurrent=1)
        provider._queue = mock_queue  # Inject mock queue

        result = asyncio.run(provider.extract(Path("test.pdf")))

        mock_queue.submit.assert_called_once_with(Path("test.pdf"), model="PaddleOCR-VL-1.6")
        assert result == expected_doc

    def test_paddle_queue_limits_concurrency_to_one(self):
        """VL 队列必须把实际 OCR 并发限制为 1。"""
        client = _FakePaddleClient()
        queue = PaddleOCRQueue(client, max_concurrent=1)

        async def _run():
            await asyncio.gather(
                queue.submit(Path("a.pdf"), model="PaddleOCR-VL-1.6"),
                queue.submit(Path("b.pdf"), model="PaddleOCR-VL-1.6"),
            )
            return queue.stats

        stats = asyncio.run(_run())

        assert client.max_active == 1
        assert stats["total_submitted"] == 2
        assert stats["total_completed"] == 2
        assert {name for name, _ in client.calls} == {"a.pdf", "b.pdf"}

    def test_paddle_queue_failure_does_not_block_next_job(self):
        """单个 OCR 失败必须抛给调用方，且不能卡死队列后续任务。"""
        client = _FlakyPaddleClient()
        queue = PaddleOCRQueue(client, max_concurrent=1)

        async def _run():
            first = asyncio.create_task(queue.submit(Path("a.pdf")))
            second = asyncio.create_task(queue.submit(Path("b.pdf")))
            results = await asyncio.gather(first, second, return_exceptions=True)
            return results, queue.stats

        (first_result, second_result), stats = asyncio.run(_run())

        assert isinstance(first_result, RuntimeError)
        assert isinstance(second_result, OcrDocument)
        assert stats["total_failed"] == 1
        assert stats["total_completed"] == 1

    def test_paddle_queue_close_cancels_worker(self):
        """close() 必须取消后台 worker，避免任务完成后 pending task 累积。"""
        client = _FakePaddleClient()
        queue = PaddleOCRQueue(client, max_concurrent=1)

        async def _run():
            await queue.submit(Path("a.pdf"))
            worker = queue._worker_task
            queue.close()
            await asyncio.sleep(0)
            return worker.done()

        assert asyncio.run(_run()) is True


class TestBuildOcrChainVLModel:
    """Tests for build_ocr_chain() with VL models."""

    @patch("app.domains.document.ocr.providers.settings")
    def test_vl_model_uses_queued_provider(self, mock_settings):
        """When model contains 'VL', should use QueuedPaddleOCRProvider."""
        mock_settings.ocr_mock_mode = False
        mock_settings.paddleocr_vl_token = "test-token"
        mock_settings.paddleocr_api_base_url = "https://example.com/api"
        mock_settings.llm_request_timeout_seconds = 60
        mock_settings.paddleocr_poll_interval_seconds = 5
        mock_settings.paddleocr_job_timeout_seconds = 600
        mock_settings.mimo_api_key = None
        mock_settings.deepseek_api_key = None
        mock_settings.deepseek_vl_model = None

        chain = build_ocr_chain(model="PaddleOCR-VL-1.6")

        assert len(chain.providers) == 1
        provider = chain.providers[0]
        assert isinstance(provider, QueuedPaddleOCRProvider)
        assert provider.model == "PaddleOCR-VL-1.6"

    @patch("app.domains.document.ocr.providers.settings")
    def test_vl_model_case_insensitive(self, mock_settings):
        """VL detection should be case-insensitive."""
        mock_settings.ocr_mock_mode = False
        mock_settings.paddleocr_vl_token = "test-token"
        mock_settings.paddleocr_api_base_url = "https://example.com/api"
        mock_settings.llm_request_timeout_seconds = 60
        mock_settings.paddleocr_poll_interval_seconds = 5
        mock_settings.paddleocr_job_timeout_seconds = 600
        mock_settings.mimo_api_key = None
        mock_settings.deepseek_api_key = None
        mock_settings.deepseek_vl_model = None

        # Test various case combinations
        for model_name in ["PaddleOCR-VL-1.6", "paddleocr-vl-1.6", "PADDLEOCR-VL", "vl-model"]:
            chain = build_ocr_chain(model=model_name)
            provider = chain.providers[0]
            assert isinstance(provider, QueuedPaddleOCRProvider), f"Failed for model: {model_name}"

    @patch("app.domains.document.ocr.providers.settings")
    def test_non_vl_model_uses_queued_client(self, mock_settings):
        """PPS 模型也走本地队列（2026-08-25：服务端队列满 10010 修复）。"""
        mock_settings.ocr_mock_mode = False
        mock_settings.paddleocr_vl_token = "test-token"
        mock_settings.paddleocr_api_base_url = "https://example.com/api"
        mock_settings.llm_request_timeout_seconds = 60
        mock_settings.paddleocr_poll_interval_seconds = 5
        mock_settings.paddleocr_job_timeout_seconds = 600
        mock_settings.mimo_api_key = None
        mock_settings.deepseek_api_key = None
        mock_settings.deepseek_vl_model = None

        chain = build_ocr_chain(model="PP-StructureV3")

        assert len(chain.providers) == 1
        provider = chain.providers[0]
        assert isinstance(provider, QueuedPaddleOCRProvider)

    @patch("app.domains.document.ocr.providers.settings")
    def test_no_model_uses_queued_client(self, mock_settings):
        """model 为 None（默认 PPS）也走本地队列。"""
        mock_settings.ocr_mock_mode = False
        mock_settings.paddleocr_vl_token = "test-token"
        mock_settings.paddleocr_api_base_url = "https://example.com/api"
        mock_settings.llm_request_timeout_seconds = 60
        mock_settings.paddleocr_poll_interval_seconds = 5
        mock_settings.paddleocr_job_timeout_seconds = 600
        mock_settings.mimo_api_key = None
        mock_settings.deepseek_api_key = None
        mock_settings.deepseek_vl_model = None

        chain = build_ocr_chain()

        assert len(chain.providers) == 1
        provider = chain.providers[0]
        assert isinstance(provider, QueuedPaddleOCRProvider)


class TestBuildOcrChainIntegration:
    """Integration tests for build_ocr_chain()."""

    @patch("app.domains.document.ocr.providers.settings")
    def test_mock_mode_returns_mock_provider(self, mock_settings):
        """When mock=True, should return MockOCRProvider."""
        mock_settings.ocr_mock_mode = True

        chain = build_ocr_chain(mock=True)

        assert len(chain.providers) == 1
        assert chain.providers[0].name == "mock"

    @patch("app.domains.document.ocr.providers.settings")
    def test_no_paddle_token_skips_paddle(self, mock_settings):
        """When paddleocr_vl_token is None, should not add PaddleOCR provider."""
        mock_settings.ocr_mock_mode = False
        mock_settings.paddleocr_vl_token = None
        mock_settings.mimo_api_key = None
        mock_settings.deepseek_api_key = None
        mock_settings.deepseek_vl_model = None

        chain = build_ocr_chain(model="PaddleOCR-VL-1.6")

        assert len(chain.providers) == 0

    @patch("app.domains.document.ocr.providers.settings")
    def test_no_vl_fallback_in_chain(self, mock_settings):
        """LLM VL 移出驱动链（2026-08-25 用户决策，OCR_PROVIDER_POLICY.md §2）。

        即使 mimo/deepseek VL 配置存在，build_ocr_chain 也不追加 VL provider：
        paddle token 存在 → 链只含 paddleocr；paddle token 缺失 → 链为空
        （无 VL 兜底，任务应标记 ocr_unavailable 等待 paddle 恢复）。
        """
        mock_settings.ocr_mock_mode = False
        mock_settings.paddleocr_vl_token = "paddle-token"
        mock_settings.paddleocr_api_base_url = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
        mock_settings.llm_request_timeout_seconds = 60
        mock_settings.paddleocr_poll_interval_seconds = 5
        mock_settings.paddleocr_job_timeout_seconds = 600
        # mimo/deepseek VL 配置齐全但不得进链
        mock_settings.mimo_api_key = "mimo-key"
        mock_settings.mimo_base_url = "https://api.xiaomimimo.com/v1"
        mock_settings.mimo_vl_model = "mimo-v2.5"
        mock_settings.deepseek_api_key = "deepseek-key"
        mock_settings.deepseek_base_url = "https://api.deepseek.com"
        mock_settings.deepseek_vl_model = "deepseek-v4-flash-vision-exp"

        chain = build_ocr_chain(model="PP-StructureV3")

        assert [p.name for p in chain.providers] == ["paddleocr"]

    @patch("app.domains.document.ocr.providers.settings")
    def test_no_vl_fallback_paddle_down_chain_empty(self, mock_settings):
        """paddle token 缺失且 VL 配置存在 → 链为空（不降级 LLM VL）。"""
        mock_settings.ocr_mock_mode = False
        mock_settings.paddleocr_vl_token = None
        mock_settings.mimo_api_key = "mimo-key"
        mock_settings.mimo_base_url = "https://api.xiaomimimo.com/v1"
        mock_settings.mimo_vl_model = "mimo-v2.5"
        mock_settings.deepseek_api_key = "deepseek-key"
        mock_settings.deepseek_base_url = "https://api.deepseek.com"
        mock_settings.deepseek_vl_model = "deepseek-v4-flash-vision-exp"

        chain = build_ocr_chain(model="PP-StructureV3")

        assert len(chain.providers) == 0

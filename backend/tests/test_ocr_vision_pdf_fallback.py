import asyncio
import json
import shutil
import uuid
from pathlib import Path

import httpx
import pytest

from app.domains.document.ocr.paddle_client import PaddleOCRClient
from app.domains.document.ocr.providers import LLMVisionOCRProvider, _data_url

# 2026-08-27：临时目录改用工作区 tmp（uuid 唯一子目录），避免沙箱对系统
# %TEMP% 的 ACL 限制（conftest 将 tempfile.tempdir 指向 %TEMP%\aitutor_pytest，
# 沙箱会话下测试进程写该目录 PermissionError）。模式与
# test_paddle_circuit_breaker._WORKSPACE_TMP / processor._download_pdf 一致。
_WORKSPACE_TMP = Path(__file__).resolve().parents[2] / "tmp" / "pytest_ocr_vision"


def _tmp_dir() -> Path:
    _WORKSPACE_TMP.mkdir(parents=True, exist_ok=True)
    d = _WORKSPACE_TMP / f"ocr_vision_{uuid.uuid4().hex[:8]}"
    d.mkdir()
    return d


class _FakeVisionGateway:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, float]] = []

    async def complete_vision(
        self,
        prompt: str,
        image_data_url: str,
        *,
        temperature: float = 0.2,
    ) -> str:
        self.calls.append((prompt, image_data_url, temperature))
        return f"# page {len(self.calls)}"


def _tmp_pdf() -> Path:
    import tempfile

    path = Path(tempfile.mktemp(suffix=".pdf"))
    path.write_bytes(b"%PDF-1.4 fake")
    return path


def test_llm_vision_ocr_renders_pdf_pages() -> None:
    fitz = pytest.importorskip("fitz")
    tmp_dir = _tmp_dir()
    pdf_path = tmp_dir / "sample.pdf"
    doc = fitz.open()
    for _ in range(2):
        page = doc.new_page()
        page.insert_text((72, 72), "sample page")
    doc.save(str(pdf_path))
    doc.close()
    try:
        gateway = _FakeVisionGateway()
        provider = LLMVisionOCRProvider(name="deepseek-vl", gateway=gateway)
        result = asyncio.run(provider.extract(pdf_path))

        assert len(result.pages) == 2
        assert [p.page_number for p in result.pages] == [1, 2]
        assert [p.markdown for p in result.pages] == ["# page 1", "# page 2"]
        assert result.provider_used == "deepseek-vl"
        assert len(gateway.calls) == 2
        assert all(url.startswith("data:image/png;base64,") for _, url, _ in gateway.calls)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_llm_vision_ocr_keeps_image_data_url() -> None:
    tmp_dir = _tmp_dir()
    image_path = tmp_dir / "sample.png"
    image_path.write_bytes(b"fake png bytes")

    try:
        gateway = _FakeVisionGateway()
        provider = LLMVisionOCRProvider(name="mimo", gateway=gateway)
        result = asyncio.run(provider.extract(image_path))

        assert len(result.pages) == 1
        assert result.pages[0].page_number == 1
        assert result.pages[0].markdown == "# page 1"
        assert gateway.calls[0][1] == _data_url(image_path)
        assert gateway.calls[0][1].startswith("data:image/png;base64,")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_submit_transient_error_retries_then_succeeds() -> None:
    """提交遇到瞬态错误（503）时按 submit_max_retries 重试后成功。

    注意：10010（队列满）不再重试 2 次后成功——8574109 起连续 2 次 10010
    触发熔断（300s）并立即降级 VL，由 test_paddle_circuit_breaker.py 覆盖；
    这里用 503 验证普通瞬态错误的重试路径。
    """
    post_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal post_count
        if request.method == "POST":
            post_count += 1
            if post_count < 3:
                return httpx.Response(503, text="service unavailable")
            return httpx.Response(200, json={"data": {"jobId": "job-q"}})
        if request.url.path.endswith("/job-q"):
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
            line = json.dumps(
                {"page": 1, "result": {"layoutParsingResults": [{"markdown": {"text": "ok"}}]}}
            )
            return httpx.Response(200, text=line)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    client = PaddleOCRClient(
        base_url="https://example.com/api/v2/ocr/jobs",
        token="secret",
        transport=transport,
        poll_interval_seconds=0,
        submit_max_retries=2,
        submit_retry_delay=0,
    )

    doc = asyncio.run(client.extract(_tmp_pdf()))

    assert post_count == 3
    assert doc.pages[0].markdown == "ok"

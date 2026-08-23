import asyncio

import httpx
import pytest

from app.ai.json_utils import parse_json_object
from app.ai.providers.http import HTTPLLMProvider, extract_completion_text


def test_parse_json_object_strips_markdown_fence() -> None:
    raw = '```json\n{"questions": []}\n```'
    assert parse_json_object(raw) == {"questions": []}


def test_parse_json_object_finds_object_after_prose() -> None:
    raw = 'result:\n{"questions": [{"question_number": "1"}]}\ndone'
    parsed = parse_json_object(raw)
    assert parsed["questions"][0]["question_number"] == "1"


def test_parse_json_object_rejects_non_object() -> None:
    with pytest.raises(ValueError):
        parse_json_object("[1, 2]")


def test_extract_completion_text_string() -> None:
    data = {"choices": [{"message": {"content": '{"ok": true}'}}]}
    assert extract_completion_text(data) == '{"ok": true}'


def test_extract_completion_text_list() -> None:
    data = {
        "choices": [
            {
                "message": {
                    "content": [{"type": "text", "text": '{"ok": true}'}]
                }
            }
        ]
    }
    assert extract_completion_text(data) == '{"ok": true}'


def test_extract_completion_text_empty_raises() -> None:
    data = {"choices": [{"message": {"content": ""}}]}
    with pytest.raises(ValueError):
        extract_completion_text(data)


def test_mimo_response_format_is_sent(monkeypatch) -> None:
    captured: dict = {}

    class FakeResponse:
        status_code = 200
        text = ""
        request = httpx.Request("POST", "https://api.example/v1/chat/completions")

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"choices": [{"message": {"content": '{"ok": true}'}}]}

    class FakeClient:
        def __init__(self, timeout: float) -> None:
            self.timeout = timeout

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *args) -> bool:
            return False

        async def post(self, url: str, *, json=None, headers=None):
            captured["url"] = url
            captured["payload"] = json
            captured["headers"] = headers
            return FakeResponse()

    monkeypatch.setattr(httpx, "AsyncClient", lambda timeout: FakeClient(timeout))

    provider = HTTPLLMProvider(
        name="mimo",
        base_url="https://api.example/v1",
        api_key="key",
        model="mimo-v2.5",
        response_format={"type": "json_object"},
        max_completion_tokens=131072,
    )
    text = asyncio.run(provider.complete("hello"))

    assert text == '{"ok": true}'
    assert captured["url"] == "https://api.example/v1/chat/completions"
    assert captured["payload"]["response_format"] == {"type": "json_object"}
    assert captured["payload"]["max_completion_tokens"] == 131072
    assert "max_tokens" not in captured["payload"]


def test_response_format_is_omitted_by_default(monkeypatch) -> None:
    captured: dict = {}

    class FakeResponse:
        status_code = 200
        text = ""
        request = httpx.Request("POST", "https://api.deepseek.com/chat/completions")

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"choices": [{"message": {"content": "plain text"}}]}

    class FakeClient:
        def __init__(self, timeout=None) -> None:
            self.timeout = timeout

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *args) -> bool:
            return False

        async def post(self, url: str, *, json=None, headers=None):
            captured["payload"] = json
            return FakeResponse()

    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)

    provider = HTTPLLMProvider(
        name="deepseek",
        base_url="https://api.deepseek.com",
        api_key="key",
        model="deepseek-v4-flash",
    )
    text = asyncio.run(provider.complete("hello"))

    assert text == "plain text"
    assert "response_format" not in captured["payload"]

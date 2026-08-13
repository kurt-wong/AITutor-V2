from typing import Any

from app.core.context import get_latency_ms, get_request_id


def build_response(data: Any) -> dict[str, Any]:
    return {
        "data": data,
        "meta": {
            "request_id": get_request_id(),
            "latency_ms": get_latency_ms(),
        },
    }


def build_error(code: str, message: str) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
        },
        "meta": {
            "request_id": get_request_id(),
            "latency_ms": get_latency_ms(),
        },
    }

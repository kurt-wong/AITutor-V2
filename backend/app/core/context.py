import time
import uuid
from contextvars import ContextVar, Token

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
started_at_var: ContextVar[float | None] = ContextVar("started_at", default=None)


def start_request() -> tuple[Token[str], Token[float | None]]:
    request_id_token = request_id_var.set(str(uuid.uuid4()))
    started_at_token = started_at_var.set(time.perf_counter())
    return request_id_token, started_at_token


def finish_request(tokens: tuple[Token[str], Token[float | None]]) -> None:
    request_id_token, started_at_token = tokens
    request_id_var.reset(request_id_token)
    started_at_var.reset(started_at_token)


def get_request_id() -> str:
    return request_id_var.get()


def get_latency_ms() -> int:
    started_at = started_at_var.get()
    if started_at is None:
        return 0
    return max(0, int((time.perf_counter() - started_at) * 1000))

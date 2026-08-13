"""Shared JSON parsing helpers for LLM responses.

LLM providers may wrap JSON in markdown fences or add short prose around the
object. Keeping one parser here avoids divergent behavior across the gateway,
document extraction, and live smoke tests.
"""

from __future__ import annotations

import json
from typing import Any


def parse_json_object(text: str) -> dict[str, Any]:
    """Extract the first JSON object from an LLM response.

    Raises ValueError when no usable JSON object is present.
    """
    if not isinstance(text, str):
        raise ValueError("LLM response must be a string")

    candidate = text.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        if lines and lines[0].lstrip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        candidate = "\n".join(lines).strip()

    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = candidate.find("{")
    end = candidate.rfind("}")
    if start < 0 or end < start:
        raise ValueError("no JSON object found")

    try:
        parsed = json.loads(candidate[start : end + 1])
    except json.JSONDecodeError as exc:
        raise ValueError("JSON object is invalid") from exc

    if not isinstance(parsed, dict):
        raise ValueError("JSON payload is not an object")
    return parsed

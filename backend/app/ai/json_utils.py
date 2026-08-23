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
    except json.JSONDecodeError:
        # LLM 输出可能被截断（末尾缺 }），尝试渐进式截断修复
        # 如果修复失败，_try_repair_truncated_json 抛出 ValueError
        parsed = _try_repair_truncated_json(candidate[start:])

    if not isinstance(parsed, dict):
        raise ValueError("JSON payload is not an object")
    return parsed


def _try_repair_truncated_json(text: str) -> dict[str, Any]:
    """尝试修复被截断的 JSON（LLM 输出中途断开）。

    策略：从最后一个 } 往前找，每次截掉一个层级，直到能解析。
    """
    # 先试原始文本
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass

    # 渐进式截断：找所有 } 的位置，从后往前试
    brace_positions = [i for i, c in enumerate(text) if c == "}"]
    for pos in reversed(brace_positions):
        candidate = text[: pos + 1]
        # 补齐缺失的括号
        open_braces = candidate.count("{") - candidate.count("}")
        open_brackets = candidate.count("[") - candidate.count("]")
        repaired = candidate + "]" * max(0, open_brackets) + "}" * max(0, open_braces)
        try:
            result = json.loads(repaired)
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            continue

    raise ValueError("JSON object is invalid (truncated and unrecoverable)")

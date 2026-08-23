"""content_hash 规范化与计算（Phase 2A Step 5）。

设计（已冻结，PHASE_2A_EXECUTION_PLAN.md Step 5）：
- content_hash = SHA256(规范化题干 + 规范化选项 + 规范化题型)
- 规范化规则：Unicode NFKC + 全角转半角 + 去空白/换行/制表 + 去常见标点 + 小写，
  保证同一道题无论排版差异（空格/标点/换行/全半角）都得到相同 hash。
- 综合题（is_composite）：子题（qno+type+answer）拼接参与 hash，
  不同子题配置视为不同题目。

确定性要求：规范化规则对空白、标点、换行、Unicode 有确定性（可复现）。
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata

# 需要去除的标点（全角/半角常见标点）
_PUNCTUATION = set(
    " \t\n\r\u3000　，。！？；：、（）()【】[]《》〈〉「」『』“”‘’\"'…—–-·•.,!?;:"
)


def normalize_text(text: str | None) -> str:
    """规范化文本：NFKC + 全角转半角 + 去空白/标点 + 小写。

    - NFKC：统一 Unicode 兼容字符（全角数字/字母 → 半角，兼容性分解）
    - 去除空白、换行、制表、常见标点
    - 小写
    """
    if not text:
        return ""
    # NFKC 归一化（全角→半角、兼容字符合并）
    s = unicodedata.normalize("NFKC", text)
    # 逐字符过滤：去空白/标点，其余保留
    chars = []
    for ch in s:
        if ch in _PUNCTUATION or ch.isspace():
            continue
        chars.append(ch.lower())
    return "".join(chars)


def normalize_options(options: list[dict] | None) -> str:
    """规范化选项列表为确定性字符串。"""
    if not options:
        return ""
    items = []
    for opt in options:
        if isinstance(opt, dict):
            label = normalize_text(str(opt.get("label", "")))
            text = normalize_text(str(opt.get("text", "")))
            items.append(f"{label}:{text}")
        else:
            items.append(normalize_text(str(opt)))
    # 排序保证选项顺序不影响 hash（同选项不同顺序视为同一题）
    return "|".join(sorted(items))


def normalize_sub_questions(sub_questions: list | None) -> str:
    """规范化子题（综合题）：qno+type+answer 拼接，排序保证确定性。"""
    if not sub_questions:
        return ""
    items = []
    for sub in sub_questions:
        if isinstance(sub, dict):
            qno = normalize_text(str(sub.get("qno", "")))
            qtype = normalize_text(str(sub.get("question_type", "")))
            answer = normalize_text(str(sub.get("answer", "")))
            items.append(f"{qno}:{qtype}:{answer}")
    return "|".join(sorted(items))


def compute_content_hash(
    *,
    stem: str | None,
    options: list[dict] | None = None,
    question_type: str | None = None,
    sub_questions: list | None = None,
) -> str:
    """计算 content_hash（SHA256，64 位 hex）。

    hash 覆盖：规范化题干 + 规范化选项 + 规范化题型 + 规范化子题。
    """
    parts = [
        normalize_text(stem),
        normalize_options(options),
        normalize_text(question_type),
        normalize_sub_questions(sub_questions),
    ]
    canonical = "\x00".join(parts)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

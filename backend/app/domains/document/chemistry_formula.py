"""Chemistry formula text normalization (P0-5)."""
from __future__ import annotations

import re

_SUBSCRIPTS = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
_SUPERSCRIPTS = str.maketrans("0123456789+-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻")
_SIGN_TO_ASCII = str.maketrans("−﹣－", "---")

_ELEMENT_SUBSCRIPT_RE = re.compile(r"([A-Za-z]{1,3}|\([A-Za-z0-9]+\))\((\d+)\)")
_TRAILING_CHARGE_RE = re.compile(r"\((\d*)([-+−﹣－])\)")
_LEADING_CHARGE_RE = re.compile(r"\(([-+−﹣－])(\d*)\)")


def _normalize_charge(match: re.Match) -> str:
    digits = match.group(1) or ""
    sign = (match.group(2) or "").translate(_SIGN_TO_ASCII)
    return f"{digits.translate(_SUPERSCRIPTS)}{sign.translate(_SUPERSCRIPTS)}"


def normalize_chemistry_formula(text: str | None) -> str | None:
    """Normalize OCR-parenthesized chemical subscripts and ion charges."""
    if not text:
        return text
    text = _ELEMENT_SUBSCRIPT_RE.sub(
        lambda m: f"{m.group(1)}{m.group(2).translate(_SUBSCRIPTS)}",
        text,
    )
    text = _TRAILING_CHARGE_RE.sub(_normalize_charge, text)
    text = _LEADING_CHARGE_RE.sub(
        lambda m: f"{m.group(1).translate(_SIGN_TO_ASCII).translate(_SUPERSCRIPTS)}{m.group(2).translate(_SUPERSCRIPTS)}",
        text,
    )
    return text


def _normalize_option(option: dict) -> dict:
    if not isinstance(option, dict):
        return option
    text = option.get("text")
    if isinstance(text, str):
        option["text"] = normalize_chemistry_formula(text) or text
    return option


def _normalize_sub_question(sub) -> None:
    if getattr(sub, "stem", None):
        sub.stem = normalize_chemistry_formula(sub.stem) or sub.stem
    if getattr(sub, "answer", None):
        sub.answer = normalize_chemistry_formula(sub.answer) or sub.answer
    if getattr(sub, "options", None):
        sub.options = [_normalize_option(o) for o in sub.options]
    for nested in (getattr(sub, "sub_sub_questions", None) or []):
        _normalize_sub_question(nested)


def normalize_chemistry_question(sq) -> None:
    """Normalize chemistry formulas on a SlicedQuestion in place."""
    if getattr(sq, "stem", None):
        sq.stem = normalize_chemistry_formula(sq.stem) or sq.stem
    if getattr(sq, "answer", None):
        sq.answer = normalize_chemistry_formula(sq.answer) or sq.answer
    if getattr(sq, "explanation", None):
        sq.explanation = normalize_chemistry_formula(sq.explanation) or sq.explanation
    if getattr(sq, "options", None):
        sq.options = [_normalize_option(o) for o in sq.options]
    for sub in (getattr(sq, "sub_questions", None) or []):
        _normalize_sub_question(sub)

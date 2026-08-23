"""Semantic marker resolution for LLM question annotations.

The LLM identifies question boundaries with short markers copied from the
source text. This module resolves those markers back to L1 line IDs so the
pipeline can slice the original document instead of trusting generated text.
"""

from __future__ import annotations

import difflib
import logging
import re
import unicodedata
from dataclasses import dataclass

from app.domains.document.schemas_l1 import L1Document, L1Line
from app.domains.document.schemas_l2 import L2QuestionAnnotation

logger = logging.getLogger(__name__)


_OPTION_LABEL_RE = re.compile(r"^[（(]?\s*([A-G])\s*[）)]?\s*[.、．]?\s*")
_STRICT_OPTION_LABEL_RE = re.compile(
    r"^[\uFF08(]?\s*([A-G])\s*(?:"
    r"[\uFF09)]\s*|[.\u3001\uFF0E]\s*|"
    r"\s+(?=[0-9$\\[{(+-])|$"
    r")"
)
_QUESTION_NUMBER_RE = re.compile(
    r"^\s*(?:[（(]\s*(\d{1,3})\s*[）)]|(\d{1,3})\s*\\?[.、．])"
)


@dataclass
class MarkerMatch:
    line_id: str
    order: int
    confidence: float
    matched_text: str


@dataclass
class StemResolution:
    line_ids: list[str]
    status: str
    confidence: float
    evidence: str


def normalize_marker_text(text: str) -> str:
    """Normalize a marker for tolerant but deterministic matching."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = text.lower()
    text = (
        text.replace("．", ".")
        .replace("（", "(")
        .replace("）", ")")
        .replace("：", ":")
        .replace("；", ";")
        .replace("，", ",")
        .replace("。", ".")
    )
    return re.sub(r"\s+", "", text)


def _fuzzy_score(marker: str, candidate: str) -> float | None:
    if not marker or not candidate:
        return None
    if marker in candidate:
        return 1.0
    matcher = difflib.SequenceMatcher(None, marker, candidate)
    matched = sum(block.size for block in matcher.get_matching_blocks())
    return matched / len(marker)


def _accept_fuzzy(marker: str, score: float | None) -> bool:
    if score is None:
        return False
    if len(marker) <= 4:
        return score >= 0.95
    if len(marker) <= 8:
        return score >= 0.9
    return score >= 0.8


def _extract_question_number(text: str) -> int | None:
    match = _QUESTION_NUMBER_RE.match(text or "")
    if not match:
        return None
    return int(match.group(1) or match.group(2))


def _validate_question_number(
    match: MarkerMatch,
    question_number: str | None,
) -> bool:
    """Reject matches whose line has a different question number.

    Only validates the matched line's question number, not the marker's.
    The marker's question number may be wrong (LLM outputs section number
    instead of question number), but the matched line's number comes from
    the document原文 and is reliable.
    """
    if not question_number:
        return True

    line_qnum = _extract_question_number(match.matched_text)
    if line_qnum is not None and str(line_qnum) != question_number:
        logger.warning(
            "matched line question number mismatch: line_qnum=%s expected=%s line=%s",
            line_qnum,
            question_number,
            match.line_id,
        )
        return False
    return True


def find_marker(
    marker: str,
    lines: list[L1Line],
    *,
    start_order: int | None = None,
    stop_order: int | None = None,
    question_number: str | None = None,
) -> MarkerMatch | None:
    """Find a marker in L1 lines, tolerating minor OCR/format differences."""
    marker_norm = normalize_marker_text(marker)
    if not marker_norm:
        return None

    candidates = [
        line
        for line in lines
        if (start_order is None or line.order >= start_order)
        and (stop_order is None or line.order < stop_order)
    ]
    if not candidates:
        return None

    # Exact substring match is always preferred.
    for line in candidates:
        if marker_norm in normalize_marker_text(line.text):
            match = MarkerMatch(
                line_id=line.line_id,
                order=line.order,
                confidence=1.0,
                matched_text=line.text,
            )
            if _validate_question_number(match, question_number):
                return match

    best: MarkerMatch | None = None
    for line in candidates:
        score = _fuzzy_score(marker_norm, normalize_marker_text(line.text))
        if best is None or (score or 0) > best.confidence:
            if score is not None:
                match = MarkerMatch(
                    line_id=line.line_id,
                    order=line.order,
                    confidence=score,
                    matched_text=line.text,
                )
                if _validate_question_number(match, question_number):
                    best = match

    # Markers sometimes span a line break in OCR output.
    for index in range(len(candidates) - 1):
        pair_text = normalize_marker_text(
            candidates[index].text + candidates[index + 1].text
        )
        score = _fuzzy_score(marker_norm, pair_text)
        if score is not None and (best is None or score > best.confidence):
            match = MarkerMatch(
                line_id=candidates[index].line_id,
                order=candidates[index].order,
                confidence=score,
                matched_text=candidates[index].text + candidates[index + 1].text,
            )
            if _validate_question_number(match, question_number):
                best = match

    if best is not None and _accept_fuzzy(marker_norm, best.confidence):
        return best
    return None


def _next_question_order(
    question_start_map: dict[int, str],
    line_by_id: dict[str, L1Line],
    start_order: int,
) -> int | None:
    orders = [
        line_by_id[line_id].order
        for line_id in question_start_map.values()
        if line_id in line_by_id and line_by_id[line_id].order > start_order
    ]
    return min(orders) if orders else None


def _first_option_order(
    question: L2QuestionAnnotation,
    lines: list[L1Line],
    start_order: int,
    stop_order: int,
) -> int | None:
    if question.question_type not in ("single_choice", "multiple_choice"):
        return None
    for line in lines:
        if line.order < start_order or line.order >= stop_order:
            continue
        if _STRICT_OPTION_LABEL_RE.match(line.text):
            return line.order
    return None


def _find_preceding_question_line(
    lines: list[L1Line],
    start_line: L1Line,
    question_number: str,
    stop_order: int,
) -> L1Line | None:
    """Find the bare question-number line before a semantic marker line."""
    for line in reversed(lines):
        if (
            line.order >= start_line.order
            or line.order < start_line.order - 3
            or line.order >= stop_order
            or line.page_no != start_line.page_no
        ):
            continue
        if str(_extract_question_number(line.text) or "") == question_number:
            return line
    return None


def resolve_stem_range(
    question: L2QuestionAnnotation,
    doc: L1Document,
    *,
    stop_order: int,
    question_start_map: dict[int, str],
) -> StemResolution | None:
    """Resolve LLM stem markers to a contiguous L1 line range.

    Returns None when there is no usable semantic marker; callers should then
    fall back to the existing LLM line-ID validation path.
    """
    start_marker = (question.stem_start_marker or "").strip()
    end_marker = (question.stem_end_marker or "").strip()
    if not start_marker and not end_marker:
        return None

    line_by_id = {line.line_id: line for line in doc.lines}
    start_match: MarkerMatch | None = None
    if start_marker:
        start_match = find_marker(
            start_marker,
            doc.lines,
            stop_order=stop_order,
            question_number=question.question_number,
        )

    start_line: L1Line | None = None
    if start_match is not None:
        start_line = line_by_id[start_match.line_id]
        expected_qnum = str(question.question_number or "")
        if (
            str(_extract_question_number(start_line.text) or "")
            != expected_qnum
        ):
            preceding = _find_preceding_question_line(
                doc.lines,
                start_line,
                expected_qnum,
                stop_order,
            )
            if preceding is not None:
                start_line = preceding

    if start_line is None:
        return None

    end_match: MarkerMatch | None = None
    if end_marker:
        end_match = find_marker(
            end_marker,
            doc.lines,
            start_order=start_line.order,
            stop_order=stop_order,
            question_number=question.question_number,
        )

    # Compute deterministic boundaries: next question, first option, answer section
    boundary_orders: list[int] = []
    next_q = _next_question_order(
        question_start_map, line_by_id, start_line.order
    )
    if next_q is not None:
        boundary_orders.append(next_q - 1)
    first_option = _first_option_order(
        question, doc.lines, start_line.order, stop_order
    )
    if first_option is not None:
        boundary_orders.append(first_option - 1)
    if stop_order != float("inf"):
        boundary_orders.append(stop_order - 1)
    if not boundary_orders:
        last_before_answer = max(
            (
                line.order
                for line in doc.lines
                if line.order < stop_order
            ),
            default=None,
        )
        if last_before_answer is not None:
            boundary_orders.append(last_before_answer)
    hard_boundary = min(boundary_orders) if boundary_orders else None

    # For choice questions with options found: stem definitively ends before
    # the first option. This is not a cap — it IS the boundary, regardless
    # of what LLM end_marker says.
    # For short_answer: stem definitively ends at next question boundary.
    has_options = first_option is not None
    is_choice = question.question_type in ("single_choice", "multiple_choice")
    is_short_answer = question.question_type in ("short_answer", "fill_in")

    if is_choice and has_options:
        end_order = first_option - 1
        # Also respect next-question boundary (guard against OCR missing options)
        if hard_boundary is not None:
            end_order = min(end_order, hard_boundary)
        end_was_capped = end_match is not None and end_match.order != end_order
    elif is_short_answer and next_q is not None:
        # short_answer: stem ends at next question boundary (deterministic)
        end_order = next_q - 1
        if stop_order != float("inf"):
            end_order = min(end_order, stop_order - 1)
        end_was_capped = end_match is not None and end_match.order != end_order
    else:
        # Use LLM end marker but cap at deterministic boundary
        end_order = end_match.order if end_match is not None else None
        if end_match is not None:
            end_line = line_by_id[end_match.line_id]
            # Treat an option label as the boundary before the options, even if the
            # LLM chose it as an approximate stem end.
            if _STRICT_OPTION_LABEL_RE.match(end_line.text):
                end_order = end_line.order - 1
        # Cap end_order at hard boundary (next question / answer section)
        if hard_boundary is not None:
            if end_order is None or end_order > hard_boundary:
                end_order = hard_boundary
        end_was_capped = (
            end_match is not None
            and hard_boundary is not None
            and end_match.order > hard_boundary
        )

    if end_order is None or end_order < start_line.order:
        return None

    line_ids = [
        line.line_id
        for line in doc.lines
        if start_line.order <= line.order <= end_order and line.order < stop_order
    ]
    if not line_ids:
        return None

    confidence = min(
        (start_match.confidence if start_match else 1.0),
        (end_match.confidence if end_match else 1.0),
    )
    status = "semantic" if confidence >= 0.999 else "fuzzy"
    evidence_parts = []
    if start_match is not None:
        evidence_parts.append(
            f"start_marker={start_match.line_id}@"
            f"{start_match.confidence:.2f}"
        )
    if start_line is not None and (
        start_match is None or start_line.line_id != start_match.line_id
    ):
        evidence_parts.append(f"start_expanded_to={start_line.line_id}")
    if is_choice and has_options:
        evidence_parts.append("end=first_option_boundary")
    elif is_short_answer and next_q is not None:
        evidence_parts.append("end=next_question_boundary")
    elif end_was_capped:
        evidence_parts.append(
            f"end_capped_at_boundary(from={end_match.line_id})"
        )
    elif end_match is not None:
        evidence_parts.append(
            f"end_marker={end_match.line_id}@{end_match.confidence:.2f}"
        )
    else:
        evidence_parts.append("end=deterministic_boundary")
    evidence = "semantic_marker " + " ".join(evidence_parts)

    return StemResolution(
        line_ids=line_ids,
        status=status,
        confidence=confidence,
        evidence=evidence,
    )


def resolve_composite_stem_range(
    question: L2QuestionAnnotation,
    doc: L1Document,
    *,
    stop_order: int,
    question_start_map: dict[int, str],
) -> StemResolution | None:
    """Resolve composite stems from shared material when semantic markers are absent.

    Composite material questions often have LLM stem_line_ids that are sparse or
    unstable. When shared material is present, use the earliest shared/stem line
    as the start and the first option or next question as the deterministic end.
    """
    line_by_id = {line.line_id: line for line in doc.lines}
    shared_ids = [
        lid for lid in question.shared_material_line_ids if lid in line_by_id
    ]
    stem_ids = [lid for lid in question.stem_line_ids if lid in line_by_id]
    orders = [
        line_by_id[lid].order
        for lid in list(dict.fromkeys(shared_ids + stem_ids))
    ]
    if not orders:
        return None

    start_order = min(orders)
    start_line = next(
        line for line in doc.lines if line.order == start_order
    )
    first_option = _first_option_order(
        question, doc.lines, start_order, stop_order
    )
    next_q = None
    for qnum, line_id in question_start_map.items():
        line = line_by_id.get(line_id)
        if (
            line is None
            or line.order <= start_order
            or str(qnum) == question.question_number
        ):
            continue
        next_q = line.order if next_q is None else min(next_q, line.order)

    boundaries: list[int] = []
    if first_option is not None:
        boundaries.append(first_option - 1)
    if next_q is not None:
        boundaries.append(next_q - 1)
    if stop_order != float("inf"):
        boundaries.append(stop_order - 1)
    if not boundaries:
        return None

    end_order = min(boundaries)
    if end_order < start_order:
        return None

    line_ids = [
        line.line_id
        for line in doc.lines
        if start_order <= line.order <= end_order and line.order < stop_order
    ]
    if not line_ids:
        return None

    if first_option is not None:
        boundary_note = "end=first_option_boundary"
    elif next_q is not None:
        boundary_note = "end=next_question_boundary"
    else:
        boundary_note = "end=answer_section_boundary"

    return StemResolution(
        line_ids=line_ids,
        status="composite",
        confidence=1.0,
        evidence=(
            f"composite_deterministic start={start_line.line_id} "
            f"{boundary_note}"
        ),
    )

"""Expected paper structure gate for live validation.

The manifest files under ``test/annotations/structure`` describe the canonical
top-level grouping of a real paper.  The validator intentionally does not
tolerate LLM grouping drift: composite boundaries, sub-question coverage and
shared material presence are structural invariants, not reproducibility noise.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STRUCTURE_DIR = ROOT / "test" / "annotations" / "structure"

PAPER_STRUCTURES = {
    "math": STRUCTURE_DIR / "math_2026_chaoyang.paper_structure.json",
    "english": STRUCTURE_DIR / "english_2026_chaoyang.paper_structure.json",
    "physics": STRUCTURE_DIR / "physics_2026_chaoyang.paper_structure.json",
    "english_dongcheng": STRUCTURE_DIR / "english_2026_dongcheng.paper_structure.json",
    "chinese": STRUCTURE_DIR / "chinese_2026_chaoyang.paper_structure.json",
    "chemistry": STRUCTURE_DIR / "chemistry_2026_bashi.paper_structure.json",
    "biology": STRUCTURE_DIR / "biology_2026_daxing.paper_structure.json",
}

SUPPORTED_KINDS = {"composite", "independent"}


def _natural_key(value: str):
    parts = re.split(r"(\d+)", value or "")
    return tuple(int(part) if part.isdigit() else part for part in parts)


def _sort_qnos(qnos):
    return sorted(qnos, key=_natural_key)


def _normalize_qno(value) -> str:
    if isinstance(value, dict):
        value = value.get("qno")
    return str(value or "").strip()


def _validate_manifest(manifest: dict) -> list[str]:
    errors: list[str] = []
    if manifest.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if not isinstance(manifest.get("subject"), str) or not manifest["subject"]:
        errors.append("subject must be a non-empty string")
    if not isinstance(manifest.get("source_file"), str) or not manifest["source_file"]:
        errors.append("source_file must be a non-empty string")

    bottom = manifest.get("bottom_question_numbers")
    if not isinstance(bottom, list) or not bottom:
        errors.append("bottom_question_numbers must be a non-empty list")
    elif len(set(bottom)) != len(bottom):
        errors.append("bottom_question_numbers contains duplicates")

    groups = manifest.get("groups")
    if not isinstance(groups, list) or not groups:
        errors.append("groups must be a non-empty list")
        return errors

    seen_top: set[str] = set()
    covered_bottom: list[str] = []
    for index, group in enumerate(groups):
        prefix = f"groups[{index}]"
        if not isinstance(group, dict):
            errors.append(f"{prefix} must be an object")
            continue
        qnum = _normalize_qno(group.get("question_number"))
        if not qnum:
            errors.append(f"{prefix}.question_number is required")
        elif qnum in seen_top:
            errors.append(f"{prefix}.question_number duplicates {qnum!r}")
        seen_top.add(qnum)

        kind = group.get("kind")
        if kind not in SUPPORTED_KINDS:
            errors.append(f"{prefix}.kind must be one of {sorted(SUPPORTED_KINDS)}")

        qtypes = group.get("question_types")
        if not isinstance(qtypes, list) or not qtypes:
            errors.append(f"{prefix}.question_types must be a non-empty list")
        elif any(not isinstance(qt, str) or not qt for qt in qtypes):
            errors.append(f"{prefix}.question_types must contain non-empty strings")

        subs = group.get("sub_questions")
        if not isinstance(subs, list):
            errors.append(f"{prefix}.sub_questions must be a list")
            continue

        sub_qnos = [_normalize_qno(item) for item in subs]
        if any(not q for q in sub_qnos):
            errors.append(f"{prefix}.sub_questions contains an empty qno")

        numbering = group.get("sub_question_numbering", "absolute")
        if numbering not in {"absolute", "relative"}:
            errors.append(f"{prefix}.sub_question_numbering must be absolute or relative")

        if kind == "composite":
            if not sub_qnos:
                errors.append(f"{prefix}.composite group must define sub_questions")
            if group.get("shared_material") != "required":
                errors.append(f"{prefix}.composite group must set shared_material=required")
        else:
            if sub_qnos:
                errors.append(f"{prefix}.independent group must not define sub_questions")
            if group.get("shared_material") != "forbidden":
                errors.append(f"{prefix}.independent group must set shared_material=forbidden")

        if kind == "composite":
            numbering = group.get("sub_question_numbering", "absolute")
            if numbering == "relative":
                covered_bottom.extend(f"{qnum}{sub}" for sub in sub_qnos)
            else:
                covered_bottom.extend(sub_qnos)
        else:
            covered_bottom.append(qnum)

    if bottom:
        expected_set = set(bottom)
        actual_set = set(covered_bottom)
        missing = expected_set - actual_set
        extra = actual_set - expected_set
        if missing:
            errors.append(f"groups do not cover bottom_question_numbers: missing={_sort_qnos(missing)}")
        if extra:
            errors.append(f"groups cover extra bottom_question_numbers: extra={_sort_qnos(extra)}")
        if len(covered_bottom) != len(set(covered_bottom)):
            dups = sorted({q for q, n in Counter(covered_bottom).items() if n > 1})
            errors.append(f"groups overlap on bottom_question_numbers: {dups}")

    return errors


def _extract_sub_qnos(question: dict) -> list[str]:
    subs = question.get("sub_questions") or []
    return [_normalize_qno(item) for item in subs]


def validate_paper_structure(run_result: dict, manifest: dict) -> dict:
    """Validate a pipeline result against a paper structure manifest.

    Returns:
        A dict with ``valid``, ``errors`` and ``stats``.  Validation is strict:
        any missing/extra top-level question, wrong composite boundary, missing
        sub-question, duplicate number or missing shared material is an error.
    """
    manifest_errors = _validate_manifest(manifest)
    if manifest_errors:
        return {
            "valid": False,
            "errors": [f"manifest invalid: {error}" for error in manifest_errors],
            "stats": {},
        }

    errors: list[str] = []
    expected_groups = manifest["groups"]
    expected_by_qnum = {_normalize_qno(g["question_number"]): g for g in expected_groups}
    expected_bottom = set(manifest["bottom_question_numbers"])

    actual_by_qnum: dict[str, dict] = {}
    for question in run_result.get("questions", []):
        qnum = _normalize_qno(question.get("question_number"))
        if not qnum:
            errors.append("question with empty question_number exists")
            continue
        if qnum in actual_by_qnum:
            errors.append(f"duplicate top-level question_number {qnum!r}")
        actual_by_qnum[qnum] = question

    for expected in expected_groups:
        qnum = _normalize_qno(expected["question_number"])
        actual = actual_by_qnum.get(qnum)
        if actual is None:
            errors.append(f"missing expected top-level question {qnum!r}")
            continue

        actual_type = str(actual.get("question_type") or "").strip()
        expected_types = expected.get("question_types") or []
        if actual_type not in expected_types:
            errors.append(
                f"Q{qnum} question_type {actual_type!r} not in expected {expected_types}"
            )

        kind = expected.get("kind")
        if kind == "composite":
            if not actual.get("is_composite"):
                errors.append(f"Q{qnum} must be is_composite=true")
            actual_subs = _extract_sub_qnos(actual)
            expected_subs = [_normalize_qno(q) for q in expected.get("sub_questions", [])]
            if actual_subs != expected_subs:
                errors.append(
                    f"Q{qnum} sub_questions {actual_subs} != expected {expected_subs}"
                )
            shared = actual.get("shared_material_line_ids") or []
            if not shared:
                errors.append(f"Q{qnum} composite must have non-empty shared_material_line_ids")
        else:
            if actual.get("is_composite"):
                errors.append(f"Q{qnum} must not be is_composite=true")
            actual_subs = _extract_sub_qnos(actual)
            if actual_subs:
                errors.append(f"Q{qnum} independent must not define sub_questions")
            shared = actual.get("shared_material_line_ids") or []
            if shared:
                errors.append(f"Q{qnum} independent must have empty shared_material_line_ids")

    extra_top = set(actual_by_qnum) - set(expected_by_qnum)
    if extra_top:
        errors.append(f"unexpected top-level questions: {_sort_qnos(extra_top)}")

    actual_bottom: list[str] = []
    for qnum, question in actual_by_qnum.items():
        if question.get("is_composite"):
            expected = expected_by_qnum.get(qnum, {})
            numbering = expected.get("sub_question_numbering", "absolute")
            sub_qnos = _extract_sub_qnos(question)
            if numbering == "relative":
                actual_bottom.extend(f"{qnum}{sub}" for sub in sub_qnos)
            else:
                actual_bottom.extend(sub_qnos)
        else:
            actual_bottom.append(qnum)

    actual_bottom_set = set(actual_bottom)
    missing_bottom = expected_bottom - actual_bottom_set
    extra_bottom = actual_bottom_set - expected_bottom
    if missing_bottom:
        errors.append(f"missing bottom-level questions: {_sort_qnos(missing_bottom)}")
    if extra_bottom:
        errors.append(f"unexpected bottom-level questions: {_sort_qnos(extra_bottom)}")
    duplicate_bottom = sorted(
        {q for q, count in Counter(actual_bottom).items() if count > 1}
    )
    if duplicate_bottom:
        errors.append(f"duplicate bottom-level questions: {duplicate_bottom}")

    composite_count = sum(
        1 for q in actual_by_qnum.values() if q.get("is_composite")
    )
    return {
        "valid": not errors,
        "errors": errors,
        "stats": {
            "top_level_count": len(actual_by_qnum),
            "expected_top_level_count": len(expected_groups),
            "composite_count": composite_count,
            "independent_count": len(actual_by_qnum) - composite_count,
            "bottom_level_count": len(actual_bottom),
            "expected_bottom_level_count": len(expected_bottom),
        },
    }


def load_manifest(subject: str) -> dict | None:
    path = PAPER_STRUCTURES.get(subject)
    if path is None or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))

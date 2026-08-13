import json
import re
from typing import Any


DOCUMENT_FIELDS = ["subject", "grade", "year", "school"]
QUESTION_FIELDS = [
    "question_number",
    "stem",
    "answer",
    "explanation",
    "question_type",
    "difficulty",
    "score",
    "images",
    "knowledge_points",
    "options",
]


def evaluate_document(expected: dict[str, Any], actual: dict[str, Any]) -> dict[str, Any]:
    expected_questions = expected.get("questions") or []
    actual_questions = actual.get("questions") or []
    question_count = max(len(expected_questions), len(actual_questions))

    question_field_totals: dict[str, int] = {
        field: 0 for field in QUESTION_FIELDS
    }
    question_field_correct: dict[str, int] = {
        field: 0 for field in QUESTION_FIELDS
    }
    per_question: list[dict[str, Any]] = []

    for index in range(question_count):
        expected_question = expected_questions[index] if index < len(expected_questions) else {}
        actual_question = actual_questions[index] if index < len(actual_questions) else {}
        field_results: dict[str, bool] = {}
        for field in QUESTION_FIELDS:
            expected_value = normalize_value(expected_question.get(field))
            actual_value = normalize_value(actual_question.get(field))
            matched = expected_value == actual_value
            field_results[field] = matched
            question_field_totals[field] += 1
            if matched:
                question_field_correct[field] += 1
        per_question.append(
            {
                "index": index + 1,
                "fields": field_results,
                "correct_count": sum(field_results.values()),
                "field_count": len(field_results),
            }
        )

    document_field_results = {
        field: {
            "correct": int(
                normalize_value(expected.get(field))
                == normalize_value(actual.get(field))
            ),
            "total": 1,
        }
        for field in DOCUMENT_FIELDS
    }
    correct = (
        sum(item["correct"] for item in document_field_results.values())
        + sum(question_field_correct.values())
    )
    total = len(DOCUMENT_FIELDS) + sum(question_field_totals.values())
    return {
        "filename": actual.get("filename") or expected.get("filename") or "",
        "expected_question_count": len(expected_questions),
        "actual_question_count": len(actual_questions),
        "question_count_match": len(expected_questions) == len(actual_questions),
        "questions": per_question,
        "document_fields": document_field_results,
        "question_fields": {
            field: {
                "correct": question_field_correct[field],
                "total": question_field_totals[field],
            }
            for field in QUESTION_FIELDS
        },
        "correct": correct,
        "total": total,
    }


def aggregate_evaluations(evaluations: list[dict[str, Any]]) -> dict[str, Any]:
    question_totals = {
        field: sum(item["question_fields"][field]["total"] for item in evaluations)
        for field in QUESTION_FIELDS
    }
    question_correct = {
        field: sum(item["question_fields"][field]["correct"] for item in evaluations)
        for field in QUESTION_FIELDS
    }
    document_totals = {
        field: sum(item["document_fields"][field]["total"] for item in evaluations)
        for field in DOCUMENT_FIELDS
    }
    document_correct = {
        field: sum(item["document_fields"][field]["correct"] for item in evaluations)
        for field in DOCUMENT_FIELDS
    }
    overall_correct = sum(question_correct.values()) + sum(document_correct.values())
    overall_total = sum(question_totals.values()) + sum(document_totals.values())
    fields = {
        field: {
            "correct": document_correct[field],
            "total": document_totals[field],
            "accuracy": _accuracy(document_correct[field], document_totals[field]),
        }
        for field in DOCUMENT_FIELDS
    }
    fields.update(
        {
            field: {
                "correct": question_correct[field],
                "total": question_totals[field],
                "accuracy": _accuracy(question_correct[field], question_totals[field]),
            }
            for field in QUESTION_FIELDS
        }
    )
    return {
        "document_count": len(evaluations),
        "question_count_total": sum(
            item["expected_question_count"] for item in evaluations
        ),
        "question_count_match": sum(
            1 for item in evaluations if item["question_count_match"]
        ),
        "overall_accuracy": _accuracy(overall_correct, overall_total),
        "correct": overall_correct,
        "total": overall_total,
        "fields": fields,
    }


def normalize_value(value: Any) -> str:
    if isinstance(value, list):
        return json.dumps(
            sorted(normalize_value(item) for item in value),
            ensure_ascii=False,
        )
    if isinstance(value, dict):
        return json.dumps(
            {key: normalize_value(item) for key, item in sorted(value.items())},
            ensure_ascii=False,
        )
    if value is None:
        return ""
    text = str(value).strip().lower()
    return re.sub(r"[\s，。；：、（）()\[\]{}“”\"'！？!?]", "", text)


def _accuracy(correct: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round(correct / total, 4)

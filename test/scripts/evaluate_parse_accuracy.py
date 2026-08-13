#!/usr/bin/env python3
"""Evaluate parsed results against human annotations and write a field-level summary."""

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.domains.document.evaluation import (  # noqa: E402
    aggregate_evaluations,
    evaluate_document,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--annotations-dir",
        type=Path,
        default=ROOT / "test" / "annotations",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=ROOT / "test" / "results" / "parsed",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "test" / "results" / "accuracy_summary.json",
    )
    args = parser.parse_args()

    annotation_files = sorted(args.annotations_dir.glob("*.json"))
    if not annotation_files:
        print(
            f"no_annotations=1 annotations_dir={args.annotations_dir} "
            "put one JSON file per PDF into this directory"
        )
        return 0

    evaluations = []
    for annotation_path in annotation_files:
        expected = json.loads(annotation_path.read_text(encoding="utf-8"))
        expected_filename = expected.get("filename") or f"{annotation_path.stem}.pdf"
        actual_path = args.results_dir / f"{expected_filename}.json"
        if not actual_path.exists():
            print(f"missing_result={actual_path}")
            continue
        actual = json.loads(actual_path.read_text(encoding="utf-8"))
        evaluations.append(evaluate_document(expected, actual))

    summary = aggregate_evaluations(evaluations)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"summary={args.output}")
    print(f"documents={summary['document_count']}")
    print(f"overall_accuracy={summary['overall_accuracy']}")
    for field in sorted(summary["fields"]):
        item = summary["fields"][field]
        print(
            f"field={field} "
            f"accuracy={item['accuracy']} "
            f"correct={item['correct']} "
            f"total={item['total']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

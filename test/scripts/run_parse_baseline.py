#!/usr/bin/env python3
"""Run the document parsing baseline and write results under test/results/parsed."""

import argparse
import asyncio
import csv
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.ai.gateway import LLMGateway  # noqa: E402
from app.ai.providers import MockLLMProvider  # noqa: E402
from app.domains.document.ocr.providers import (  # noqa: E402
    MockOCRProvider,
    OCRFallbackChain,
    build_ocr_chain,
)
from app.domains.document.parser import DocumentParser  # noqa: E402
from app.domains.document.question_extractor import LLMQuestionExtractor  # noqa: E402


def build_parser(*, mock: bool) -> DocumentParser:
    if not mock:
        return DocumentParser(
            ocr_chain=build_ocr_chain(mock=False),
            question_extractor=LLMQuestionExtractor(),
        )

    sample_markdown = (ROOT / "test" / "fixtures" / "mock_ocr_markdown.md").read_text(
        encoding="utf-8"
    )
    sample_json = (
        ROOT / "test" / "fixtures" / "mock_question_aggregate.json"
    ).read_text(encoding="utf-8")
    return DocumentParser(
        ocr_chain=OCRFallbackChain([MockOCRProvider(markdown=sample_markdown)]),
        question_extractor=LLMQuestionExtractor(
            gateway=LLMGateway(
                mode="live",
                providers=[MockLLMProvider(response=sample_json)],
            )
        ),
    )


async def run(
    *,
    manifest_path: Path,
    output_dir: Path,
    subject: str | None,
    limit: int | None,
    mock: bool,
) -> int:
    parser = build_parser(mock=mock)
    output_dir.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    processed = 0
    failed = 0
    for row in rows:
        filename = row["filename"]
        if subject and row["subject"] != subject:
            continue
        file_path = manifest_path.parent / filename
        try:
            aggregate = await parser.parse_pdf(
                file_path,
                filename=filename,
                subject=row.get("subject") or None,
                year=_int(row.get("year")),
                school=row.get("school") or None,
            )
            payload = aggregate.model_dump(mode="json")
        except Exception as exc:
            payload = {
                "filename": filename,
                "error": str(exc),
                "questions": [],
            }
            failed += 1
        (output_dir / f"{filename}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        processed += 1
        if limit is not None and processed >= limit:
            break

    print(f"processed={processed}")
    print(f"failed={failed}")
    print(f"output_dir={output_dir}")
    return 0


def _int(value: str) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mock", action="store_true", help="use deterministic fixture")
    parser.add_argument("--subject", default=None, help="filter by subject")
    parser.add_argument("--limit", type=int, default=None, help="max files to process")
    args = parser.parse_args()

    manifest_path = ROOT / "test" / "pdf" / "manifest.csv"
    output_dir = ROOT / "test" / "results" / "parsed"
    return asyncio.run(
        run(
            manifest_path=manifest_path,
            output_dir=output_dir,
            subject=args.subject,
            limit=args.limit,
            mock=args.mock,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate test/pdf against its canonical manifest."""

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PDF_DIR = ROOT / "test" / "pdf"
MANIFEST_PATH = PDF_DIR / "manifest.csv"
EXPECTED_PDF_COUNT = 30
EXPECTED_SUBJECTS = {"数学", "物理", "化学", "英语", "语文", "生物", "政治", "历史", "地理"}


def main() -> int:
    if not MANIFEST_PATH.exists():
        print(f"missing_manifest={MANIFEST_PATH}")
        return 1

    with MANIFEST_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    errors = []
    if len(rows) != EXPECTED_PDF_COUNT:
        errors.append(f"expected {EXPECTED_PDF_COUNT} PDFs, got {len(rows)}")

    filenames = set()
    subjects = set()
    for row in rows:
        filename = row["filename"]
        path = PDF_DIR / filename
        if filename in filenames:
            errors.append(f"duplicate filename: {filename}")
        filenames.add(filename)
        if not path.exists():
            errors.append(f"missing file: {filename}")
            continue
        size_bytes = int(row["size_bytes"])
        if path.stat().st_size != size_bytes:
            errors.append(f"size mismatch: {filename}")
        subject = row["subject"]
        subjects.add(subject)
        if subject not in EXPECTED_SUBJECTS:
            errors.append(f"unknown subject: {subject}")

    missing_subjects = EXPECTED_SUBJECTS - subjects
    if missing_subjects:
        errors.append(f"missing subjects: {sorted(missing_subjects)}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(f"manifest={MANIFEST_PATH}")
    print(f"pdf_count={len(rows)}")
    print(f"subjects={sorted(subjects)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

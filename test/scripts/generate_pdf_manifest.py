#!/usr/bin/env python3
"""Generate the canonical manifest for test/pdf assets."""

import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PDF_DIR = ROOT / "test" / "pdf"
MANIFEST_PATH = PDF_DIR / "manifest.csv"

SUBJECT_KEYWORDS = [
    ("数学", "数学"),
    ("物理", "物理"),
    ("化学", "化学"),
    ("英语", "英语"),
    ("语文", "语文"),
    ("生物", "生物"),
    ("政治", "政治"),
    ("历史", "历史"),
    ("地理", "地理"),
]


def infer_subject(filename: str) -> str:
    for keyword, subject in SUBJECT_KEYWORDS:
        if keyword in filename:
            return subject
    return "unknown"


def main() -> int:
    rows = []
    for path in sorted(PDF_DIR.glob("*.pdf")):
        stats = path.stat()
        year_match = re.search(r"(20\d{2})", path.name)
        rows.append(
            {
                "filename": path.name,
                "size_bytes": stats.st_size,
                "subject": infer_subject(path.name),
                "year": year_match.group(1) if year_match else "",
                "school": "",
                "has_answer": "教师版" in path.name,
                "has_images": "",
            }
        )

    with MANIFEST_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "filename",
                "size_bytes",
                "subject",
                "year",
                "school",
                "has_answer",
                "has_images",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"manifest={MANIFEST_PATH}")
    print(f"pdf_count={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

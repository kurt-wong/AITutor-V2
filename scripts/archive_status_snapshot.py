#!/usr/bin/env python3
"""Snapshot current status docs before a versioned state rewrite.

Usage:
    python scripts/archive_status_snapshot.py
    python scripts/archive_status_snapshot.py --version 6.12

The script copies RESTART_PROMPT.md and PROJECT_STATUS.md to
docs_archive/status/<YYYY-MM-DD>_<NAME>_v<version>.md. It never overwrites
an existing snapshot with the same target name.
"""

from __future__ import annotations

import argparse
import re
import shutil
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATUS_ARCHIVE = ROOT / "docs_archive" / "status"
STATUS_DOCS = {
    "RESTART_PROMPT.md": ROOT / "RESTART_PROMPT.md",
    "PROJECT_STATUS.md": ROOT / "PROJECT_STATUS.md",
}

_VERSION_RE = re.compile(r"^Version:\s*([0-9]+(?:\.[0-9]+)+)", re.IGNORECASE)


def _current_version() -> str:
    restart_path = STATUS_DOCS["RESTART_PROMPT.md"]
    text = restart_path.read_text(encoding="utf-8")
    match = _VERSION_RE.search(text)
    if not match:
        raise SystemExit(
            "Cannot find 'Version:' in RESTART_PROMPT.md; pass --version explicitly"
        )
    return match.group(1)


def _target_name(doc_name: str, stamp: str, version: str) -> str:
    stem = doc_name.removesuffix(".md")
    return f"{stamp}_{stem}_v{version}.md"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", help="Version to embed in snapshot filenames")
    parser.add_argument(
        "--date",
        default=date.today().isoformat(),
        help="Snapshot date, default YYYY-MM-DD",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be copied without writing files",
    )
    args = parser.parse_args()

    version = args.version or _current_version()
    stamp = args.date
    STATUS_ARCHIVE.mkdir(parents=True, exist_ok=True)

    created: list[Path] = []
    skipped: list[Path] = []
    for doc_name, source_path in STATUS_DOCS.items():
        if not source_path.exists():
            print(f"skip missing source: {source_path}")
            continue
        target = STATUS_ARCHIVE / _target_name(doc_name, stamp, version)
        if target.exists():
            skipped.append(target)
            print(f"skip existing snapshot: {target}")
            continue
        if args.dry_run:
            print(f"would copy {doc_name} -> {target}")
            continue
        shutil.copy2(source_path, target)
        created.append(target)
        print(f"archived {doc_name} -> {target}")

    print(
        f"status snapshot complete: version={version}, date={stamp}, "
        f"created={len(created)}, skipped={len(skipped)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

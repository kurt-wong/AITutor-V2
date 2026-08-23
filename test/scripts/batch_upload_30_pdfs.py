"""Batch upload 30 teacher-version PDFs to the backend for real ingestion validation.

Usage (from project root, after backend is running):
    python test/scripts/batch_upload_30_pdfs.py

Reads test/pdf/manifest.csv (filename,size_bytes,subject,year,school,has_answer,has_images),
uploads each PDF via POST /api/admin/documents/upload with subject/grade/year metadata,
and saves per-file responses to test/results/batch_upload_30_pdfs.json for later
data-flow auditing.
"""

import csv
import json
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
PDF_DIR = ROOT / "test" / "pdf"
MANIFEST = PDF_DIR / "manifest.csv"
RESULTS_DIR = ROOT / "test" / "results"
OUTPUT_JSON = RESULTS_DIR / "batch_upload_30_pdfs.json"
BASE_URL = "http://127.0.0.1:8000"
UPLOAD_URL = f"{BASE_URL}/api/admin/documents/upload"

# grade 不在 manifest 中，统一按高一（全部 30 份均为高一上学期期末卷）
GRADE = "高一"


def load_manifest() -> list[dict]:
    rows = []
    with open(MANIFEST, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows


async def upload_one(client: httpx.AsyncClient, row: dict) -> dict:
    filename = row["filename"]
    pdf_path = PDF_DIR / filename
    if not pdf_path.exists():
        return {"filename": filename, "ok": False, "error": "file not found"}

    subject = (row.get("subject") or "").strip() or None
    year_raw = (row.get("year") or "").strip()
    year = int(year_raw) if year_raw.isdigit() else None

    files = {"files": (filename, pdf_path.read_bytes(), "application/pdf")}
    data = {}
    if subject:
        data["subject"] = subject
    if GRADE:
        data["grade"] = GRADE
    if year:
        data["year"] = str(year)

    resp = await client.post(UPLOAD_URL, files=files, data=data, timeout=120)
    try:
        body = resp.json()
    except Exception:
        body = {"raw": resp.text[:500]}
    return {
        "filename": filename,
        "subject": subject,
        "grade": GRADE,
        "year": year,
        "http_status": resp.status_code,
        "ok": resp.status_code == 200 and body.get("data", {}).get("status") == "queued",
        "document_id": (body.get("data") or {}).get("document_ids", [None])[0],
        "task_id": (body.get("data") or {}).get("task_ids", [None])[0],
        "body": body,
    }


async def main() -> None:
    rows = load_manifest()
    print(f"manifest rows: {len(rows)}")
    if len(rows) != 30:
        print(f"WARNING: expected 30 PDFs, got {len(rows)}")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    async with httpx.AsyncClient(timeout=120) as client:
        for idx, row in enumerate(rows, 1):
            r = await upload_one(client, row)
            results.append(r)
            tag = "OK " if r["ok"] else "ERR"
            print(
                f"[{idx:02d}/30] {tag} {r['filename'][:46]} "
                f"subject={r['subject']} year={r['year']} "
                f"http={r['http_status']} doc={str(r['document_id'])[:8]}"
            )
            time.sleep(0.3)

    ok_count = sum(1 for r in results if r["ok"])
    OUTPUT_JSON.write_text(
        json.dumps({"total": len(results), "ok": ok_count, "results": results},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nsummary: {ok_count}/{len(results)} uploaded OK -> {OUTPUT_JSON}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())

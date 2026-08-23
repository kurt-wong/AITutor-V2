"""P4E Pilot: upload 10 PDFs to backend API."""
import http.client
import json
import os
import sys
from pathlib import Path

BASE_HOST = "localhost"
BASE_PORT = 8000
PDF_DIR = Path(r"D:\Project\AITutors-v2\test\pdf")

PILOTS = [
    ("2026\u5317\u4eac\u4e8c\u4e2d\u9ad8\u4e00\uff08\u4e0a\uff09\u671f\u672b\u6570\u5b66\uff08\u6559\u5e08\u7248\uff09.pdf", "\u6570\u5b66", "\u9ad8\u4e00", 2026),
    ("2026\u5317\u4eac\u671d\u9633\u9ad8\u4e00\uff08\u4e0a\uff09\u671f\u672b\u6570\u5b66\uff08\u6559\u5e08\u7248\uff09.pdf", "\u6570\u5b66", "\u9ad8\u4e00", 2026),
    ("2026\u5317\u4eac\u671d\u9633\u9ad8\u4e00\uff08\u4e0a\uff09\u671f\u672b\u7269\u7406\uff08\u6559\u5e08\u7248\uff09.pdf", "\u7269\u7406", "\u9ad8\u4e00", 2026),
    ("2026\u5317\u4eac\u516b\u5341\u4e2d\u9ad8\u4e00\uff08\u4e0a\uff09\u671f\u672b\u7269\u7406\uff08\u6559\u5e08\u7248\uff09.pdf", "\u7269\u7406", "\u9ad8\u4e00", 2026),
    ("2026\u5317\u4eac\u516b\u4e00\u5b66\u6821\u9ad8\u4e00\uff08\u4e0a\uff09\u671f\u672b\u5316\u5b66\uff08\u6559\u5e08\u7248\uff09.pdf", "\u5316\u5b66", "\u9ad8\u4e00", 2026),
    ("2026\u5317\u4eac\u516b\u5341\u4e2d\u9ad8\u4e00\uff08\u4e0a\uff09\u671f\u672b\u5316\u5b66\uff08\u6559\u5e08\u7248\uff09.pdf", "\u5316\u5b66", "\u9ad8\u4e00", 2026),
    ("2026\u5317\u4eac\u671d\u9633\u9ad8\u4e00\uff08\u4e0a\uff09\u671f\u672b\u82f1\u8bed\uff08\u6559\u5e08\u7248\uff09.pdf", "\u82f1\u8bed", "\u9ad8\u4e00", 2026),
    ("2026\u5317\u4eac\u623f\u5c71\u9ad8\u4e00\uff08\u4e0a\uff09\u671f\u672b\u82f1\u8bed\uff08\u6559\u5e08\u7248\uff09.pdf", "\u82f1\u8bed", "\u9ad8\u4e00", 2026),
    ("2026\u5317\u4eac\u516b\u5341\u4e2d\u9ad8\u4e00\uff08\u4e0a\uff09\u671f\u672b\u8bed\u6587\uff08\u6559\u5e08\u7248\uff09.pdf", "\u8bed\u6587", "\u9ad8\u4e00", 2026),
    ("2026\u5317\u4eac\u5927\u5174\u9ad8\u4e00\uff08\u4e0a\uff09\u671f\u672b\u8bed\u6587\uff08\u6559\u5e08\u7248\uff09.pdf", "\u8bed\u6587", "\u9ad8\u4e00", 2026),
]


def upload_one(filename, subject, grade, year):
    pdf_path = PDF_DIR / filename
    if not pdf_path.exists():
        return {"filename": filename, "error": "file not found: " + str(pdf_path)}

    boundary = "----P4EBoundary"
    parts = []

    # files field
    parts.append(("--" + boundary).encode())
    parts.append(
        ('Content-Disposition: form-data; name="files"; filename="' + filename + '"').encode()
    )
    parts.append(b"Content-Type: application/pdf")
    parts.append(b"")
    parts.append(pdf_path.read_bytes())

    # subject
    parts.append(("--" + boundary).encode())
    parts.append(b'Content-Disposition: form-data; name="subject"')
    parts.append(b"")
    parts.append(subject.encode("utf-8"))

    # grade
    parts.append(("--" + boundary).encode())
    parts.append(b'Content-Disposition: form-data; name="grade"')
    parts.append(b"")
    parts.append(grade.encode("utf-8"))

    # year
    parts.append(("--" + boundary).encode())
    parts.append(b'Content-Disposition: form-data; name="year"')
    parts.append(b"")
    parts.append(str(year).encode())

    # closing
    parts.append(("--" + boundary + "--").encode())
    parts.append(b"")

    # join with CRLF
    crlf = b"\r\n"
    body = crlf.join(parts)

    conn = http.client.HTTPConnection(BASE_HOST, BASE_PORT, timeout=120)
    try:
        conn.request(
            "POST",
            "/api/admin/documents/upload",
            body=body,
            headers={"Content-Type": "multipart/form-data; boundary=" + boundary},
        )
        resp = conn.getresponse()
        data = json.loads(resp.read().decode("utf-8"))
        return {"filename": filename, "status": resp.status, "data": data.get("data")}
    except Exception as e:
        return {"filename": filename, "error": str(e)[:200]}
    finally:
        conn.close()


def main():
    results = []
    for filename, subject, grade, year in PILOTS:
        print("uploading", filename, "(" + subject + ")...", end=" ", flush=True)
        r = upload_one(filename, subject, grade, year)
        if r.get("error"):
            print("FAILED:", r["error"])
        else:
            doc_ids = r.get("data", {}).get("document_ids", [])
            print("OK ->", doc_ids)
        results.append(r)

    out = Path(r"D:\Project\AITutors-v2\test\results") / "p4e_pilot_upload.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nresults saved to", out)
    ok = sum(1 for r in results if not r.get("error"))
    fail = sum(1 for r in results if r.get("error"))
    print("success:", ok, "failed:", fail)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""上传生物 PDF 触发管线。"""
import sys
import io
import asyncio
import aiohttp
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

async def main():
    pdf_path = Path(r"test/pdf/2026北京北师大附中高一（上）期末生物（教师版）.pdf")
    if not pdf_path.exists():
        print(f"PDF not found: {pdf_path}")
        return

    print(f"Uploading: {pdf_path.name} ({pdf_path.stat().st_size} bytes)")

    async with aiohttp.ClientSession() as session:
        data = aiohttp.FormData()
        data.add_field(
            "files",
            open(pdf_path, "rb"),
            filename=pdf_path.name,
            content_type="application/pdf",
        )
        async with session.post(
            "http://localhost:8000/api/admin/documents/upload",
            data=data,
            timeout=aiohttp.ClientTimeout(total=60),
        ) as resp:
            print(f"Status: {resp.status}")
            body = await resp.text()
            print(f"Response: {body[:500]}")

asyncio.run(main())

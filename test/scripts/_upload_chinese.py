#!/usr/bin/env python3
"""上传语文 PDF 触发管线。"""
import asyncio
import io
import sys
from pathlib import Path

import aiohttp

if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


async def main():
    pdf_path = Path(r"test/pdf/2026北京朝阳高一（上）期末语文（教师版）.pdf")
    async with aiohttp.ClientSession() as session:
        data = aiohttp.FormData()
        data.add_field("subject", "语文")
        data.add_field(
            "files", open(pdf_path, "rb"),
            filename=pdf_path.name, content_type="application/pdf",
        )
        async with session.post(
            "http://localhost:8000/api/admin/documents/upload",
            data=data, timeout=aiohttp.ClientTimeout(total=60),
        ) as resp:
            print(f"Status: {resp.status}")
            print(await resp.text())


asyncio.run(main())

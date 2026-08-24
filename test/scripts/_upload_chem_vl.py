#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""上传化学 PDF 触发 VL 重跑（PaddleOCR-VL-1.6）。"""
import asyncio
import io
import sys
from pathlib import Path

import aiohttp

if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


async def main():
    pdf_path = Path(r"test/pdf/2026北京八一学校高一（上）期末化学（教师版）.pdf")
    async with aiohttp.ClientSession() as session:
        data = aiohttp.FormData()
        data.add_field("subject", "化学")
        data.add_field("ocr_model", "PaddleOCR-VL-1.6")
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

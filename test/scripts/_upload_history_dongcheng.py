#!/usr/bin/env python3
"""上传东城历史 PDF 触发管线（重跑试修 Q37 缺库：L2 锚点标注失败类）。"""
import asyncio
import io
import sys
from pathlib import Path

import aiohttp

if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


async def main():
    pdf_path = Path(r"test/pdf/2025北京东城高一（上）期末历史（教师版）.pdf")
    async with aiohttp.ClientSession() as session:
        data = aiohttp.FormData()
        data.add_field("subject", "历史")
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

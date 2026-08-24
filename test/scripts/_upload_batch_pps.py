#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量 PPS 重跑：语文/化学/政治/英语/地理/生物（统一数据源）。"""
import asyncio
import io
import sys
from pathlib import Path

import aiohttp

if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

TARGETS = [
    ("语文", "test/pdf/2026北京朝阳高一（上）期末语文（教师版）.pdf"),
    ("化学", "test/pdf/2026北京八一学校高一（上）期末化学（教师版）.pdf"),
    ("政治", "test/pdf/2026北京东城高一（上）期末政治（教师版）.pdf"),
    ("英语", "test/pdf/2026北京东城高一（上）期末英语（教师版）.pdf"),
    ("地理", "test/pdf/2026北京朝阳高一（上）期末地理（教师版）.pdf"),
    ("生物", "test/pdf/2026北京北师大附中高一（上）期末生物（教师版）.pdf"),
]


async def upload(session: aiohttp.ClientSession, subject: str, pdf: str) -> None:
    path = Path(pdf)
    data = aiohttp.FormData()
    data.add_field("subject", subject)
    data.add_field("files", open(path, "rb"), filename=path.name, content_type="application/pdf")
    async with session.post(
        "http://localhost:8000/api/admin/documents/upload",
        data=data, timeout=aiohttp.ClientTimeout(total=60),
    ) as resp:
        body = await resp.text()
        print(f"{subject}: status={resp.status} {body[:200]}")


async def main() -> None:
    async with aiohttp.ClientSession() as session:
        for subject, pdf in TARGETS:
            try:
                await upload(session, subject, pdf)
            except Exception as e:
                print(f"{subject}: ERR {e}")


asyncio.run(main())

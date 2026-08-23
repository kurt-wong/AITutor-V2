#!/usr/bin/env python3
"""直接测试 paddle API 请求，复现 400 错误。"""
import sys, io, json, asyncio
import httpx
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE_URL = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
TOKEN = "5e6b7c1269811b4177fb6a7770a2ccfddb1029cc"
MODEL = "PP-StructureV3"

async def main():
    # 用真实英语 PDF 测试
    file_path = Path(r"test/pdf/2026北京东城高一（上）期末英语（教师版）.pdf")
    print("File:", file_path.name, file_path.stat().st_size)

    headers = {"Authorization": f"bearer {TOKEN}"}
    data = {
        "model": MODEL,
        "optionalPayload": json.dumps({
            "useDocOrientationClassify": False,
            "useDocUnwarping": False,
            "useChartRecognition": False,
        }),
    }
    print("Data:", data)

    async with httpx.AsyncClient(timeout=60) as client:
        with file_path.open("rb") as f:
            response = await client.post(
                BASE_URL,
                headers=headers,
                data=data,
                files={"file": (file_path.name, f, "application/pdf")},
            )
        print("Status:", response.status_code)
        print("Body:", response.text[:500])

asyncio.run(main())

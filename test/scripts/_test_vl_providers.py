#!/usr/bin/env python3
"""测试 VL OCR 提供方（mimo-vl / deepseek-vl）是否可用。"""
import sys, io, json, asyncio
import httpx
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

MIMO_BASE = "https://api.xiaomimimo.com/v1"
MIMO_KEY = "sk-cnolie3bj6swyssiji0dpuehvuop18csfqfph5a36hrxvpm0"
MIMO_MODEL = "mimo-v2.5"

DEEPSEEK_BASE = "https://api.deepseek.com"
DEEPSEEK_KEY = "sk-96521bea50fb4eac88288e11e4415402"
DEEPSEEK_MODEL = "deepseek-v4-flash-vision-exp"

async def main():
    file_path = Path(r"test/pdf/2026北京东城高一（上）期末英语（教师版）.pdf")
    img_bytes = file_path.read_bytes()

    # 1. mimo-vl chat completions
    print("=== mimo-vl ===")
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{MIMO_BASE}/chat/completions",
                headers={"Authorization": f"Bearer {MIMO_KEY}"},
                json={
                    "model": MIMO_MODEL,
                    "messages": [{"role": "user", "content": "hi"}],
                    "max_tokens": 10,
                },
            )
            print("Status:", resp.status_code)
            print("Body:", resp.text[:300])
    except Exception as e:
        print("Error:", e)

    # 2. deepseek-vl chat completions
    print("\n=== deepseek-vl ===")
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{DEEPSEEK_BASE}/chat/completions",
                headers={"Authorization": f"Bearer {DEEPSEEK_KEY}"},
                json={
                    "model": DEEPSEEK_MODEL,
                    "messages": [{"role": "user", "content": "hi"}],
                    "max_tokens": 10,
                },
            )
            print("Status:", resp.status_code)
            print("Body:", resp.text[:300])
    except Exception as e:
        print("Error:", e)

asyncio.run(main())

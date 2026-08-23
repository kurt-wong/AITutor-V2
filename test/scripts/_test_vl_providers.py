#!/usr/bin/env python3
"""测试 VL OCR 提供方（mimo-vl / deepseek-vl）是否可用。

密钥从 backend/.env 读取，禁止硬编码。
"""
import sys, io, json, asyncio, os
import httpx
from pathlib import Path
from dotenv import load_dotenv

if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# 加载 backend/.env（含 API key）
load_dotenv(Path(__file__).resolve().parents[2] / "backend" / ".env")

MIMO_BASE = os.environ.get("MIMO_BASE_URL", "https://api.xiaomimimo.com/v1")
MIMO_KEY = os.environ.get("MIMO_API_KEY", "")
MIMO_MODEL = os.environ.get("MIMO_VL_MODEL", "mimo-v2.5")

DEEPSEEK_BASE = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_VL_MODEL", "deepseek-v4-flash-vision-exp")

if not MIMO_KEY or not DEEPSEEK_KEY:
    print("ERROR: MIMO_API_KEY / DEEPSEEK_API_KEY not found in backend/.env")
    sys.exit(1)

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

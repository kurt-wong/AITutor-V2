#!/usr/bin/env python3
"""单独测试 mimo-vl timeout=300 是否稳定断连。

密钥从 backend/.env 读取，禁止硬编码。
"""
import sys, io, json, asyncio, base64, os
import httpx
from pathlib import Path
from dotenv import load_dotenv

if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

load_dotenv(Path(__file__).resolve().parents[2] / "backend" / ".env")

MIMO_BASE = os.environ.get("MIMO_BASE_URL", "https://api.xiaomimimo.com/v1")
MIMO_KEY = os.environ.get("MIMO_API_KEY", "")
MIMO_MODEL = os.environ.get("MIMO_VL_MODEL", "mimo-v2.5")
if not MIMO_KEY:
    raise SystemExit("MIMO_API_KEY not found in backend/.env")

async def test_once(timeout: float, label: str, i: int):
    import fitz
    pdf_path = Path(r"test/pdf/2026北京东城高一（上）期末英语（教师版）.pdf")
    doc = fitz.open(str(pdf_path))
    page = doc[0]
    pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
    img_bytes = pix.tobytes("png")
    doc.close()

    b64 = base64.b64encode(img_bytes).decode("ascii")
    data_url = f"data:image/png;base64,{b64}"

    payload = {
        "model": MIMO_MODEL,
        "messages": [
            {"role": "user", "content": [
                {"type": "text", "text": "OCR this page to Markdown."},
                {"type": "image_url", "image_url": {"url": data_url}},
            ]},
        ],
        "max_tokens": 2000,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{MIMO_BASE}/chat/completions",
                headers={"Authorization": f"Bearer {MIMO_KEY}"},
                json=payload,
            )
            print(f"[{label}] #{i} timeout={timeout}: Status {resp.status_code}")
            return True
    except Exception as e:
        print(f"[{label}] #{i} timeout={timeout}: {type(e).__name__} {str(e)[:100]}")
        return False

async def main():
    # 3 次 timeout=300
    for i in range(1, 4):
        await test_once(300, "t300", i)
    # 3 次 timeout=60
    for i in range(1, 4):
        await test_once(60, "t60", i)

asyncio.run(main())

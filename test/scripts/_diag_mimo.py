#!/usr/bin/env python3
"""诊断 mimo-vl 断连：测试不同图片尺寸。

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

async def test_image(pix_zoom: float, timeout: float, label: str):
    import fitz
    pdf_path = Path(r"test/pdf/2026北京东城高一（上）期末英语（教师版）.pdf")
    doc = fitz.open(str(pdf_path))
    page = doc[0]
    pix = page.get_pixmap(matrix=fitz.Matrix(pix_zoom, pix_zoom))
    img_bytes = pix.tobytes("png")
    doc.close()
    print(f"\n=== {label}: zoom={pix_zoom} img={len(img_bytes)}B timeout={timeout}s ===")

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
            print("Status:", resp.status_code)
            print("Body:", resp.text[:200])
    except Exception as e:
        print("Error:", type(e).__name__, str(e)[:200])

async def main():
    await test_image(1.0, 60, "zoom 1.0 (small)")
    await test_image(2.0, 60, "zoom 2.0 (medium)")
    await test_image(2.0, 300, "zoom 2.0 long timeout")

asyncio.run(main())

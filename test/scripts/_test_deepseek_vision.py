#!/usr/bin/env python3
"""测试 deepseek-vl 视觉请求（图片输入）。

密钥从 backend/.env 读取，禁止硬编码。
"""
import sys, io, json, asyncio, base64, os
import httpx
from pathlib import Path
from dotenv import load_dotenv

if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

load_dotenv(Path(__file__).resolve().parents[2] / "backend" / ".env")

DEEPSEEK_BASE = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_VL_MODEL", "deepseek-v4-flash-vision-exp")
if not DEEPSEEK_KEY:
    raise SystemExit("DEEPSEEK_API_KEY not found in backend/.env")

async def main():
    import fitz
    pdf_path = Path(r"test/pdf/2026北京东城高一（上）期末英语（教师版）.pdf")
    doc = fitz.open(str(pdf_path))
    page = doc[0]
    pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
    img_bytes = pix.tobytes("png")
    doc.close()
    print("Image size:", len(img_bytes), "bytes")

    b64 = base64.b64encode(img_bytes).decode("ascii")
    data_url = f"data:image/png;base64,{b64}"

    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "识别这张图片中的文字内容，输出为 markdown。"},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
        "max_tokens": 500,
    }

    async with httpx.AsyncClient(timeout=120) as client:
        try:
            resp = await client.post(
                f"{DEEPSEEK_BASE}/chat/completions",
                headers={"Authorization": f"Bearer {DEEPSEEK_KEY}"},
                json=payload,
            )
            print("Status:", resp.status_code)
            print("Body:", resp.text[:500])
        except Exception as e:
            print("Error:", type(e).__name__, str(e))

asyncio.run(main())

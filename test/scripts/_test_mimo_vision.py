#!/usr/bin/env python3
"""测试 mimo-vl 视觉请求（图片输入）。"""
import sys, io, json, asyncio, base64
import httpx
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

MIMO_BASE = "https://api.xiaomimimo.com/v1"
MIMO_KEY = "sk-cnolie3bj6swyssiji0dpuehvuop18csfqfph5a36hrxvpm0"
MIMO_MODEL = "mimo-v2.5"

async def main():
    # 用第一页 PDF 渲染 PNG（模拟管线做法）
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
        "model": MIMO_MODEL,
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
                f"{MIMO_BASE}/chat/completions",
                headers={"Authorization": f"Bearer {MIMO_KEY}"},
                json=payload,
            )
            print("Status:", resp.status_code)
            print("Body:", resp.text[:500])
        except Exception as e:
            print("Error:", type(e).__name__, str(e))

asyncio.run(main())

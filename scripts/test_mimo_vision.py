import asyncio
import httpx
import json
import base64
from pathlib import Path

# 配置 (从 backend/.env 提取或直接硬编码测试用)
API_KEY = "sk-cp5cr7u3g4yz30v7sr5xybfr5xvxnkokd06212345" # 示例，请替换为真实 key 或从环境变量读取
BASE_URL = "https://api.xiaomimimo.com/v1"
MODEL = "mimo-v2.5" # 或者尝试 mimo-vl

async def test_vision():
    # 构造一个极小的 1x1 PNG
    import struct
    def make_tiny_png():
        # 1x1 white pixel PNG
        def chunk(chunk_type, data):
            c = chunk_type + data
            crc = struct.pack('>I', 0xFFFFFFFF & 0) # Simplified CRC
            return struct.pack('>I', len(data)) + c + crc
        
        header = b'\x89PNG\r\n\x1a\n'
        ihdr = chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
        raw = b'\x00\xff\xff\xff'
        idat = chunk(b'IDAT', b'\x08\x1d\x01\x02\x00\xfd\xff\x00\x00\x00\x02\x00\x01') # Compressed
        iend = chunk(b'IEND', b'')
        return header + ihdr + idat + iend

    img_bytes = make_tiny_png()
    b64_img = base64.b64encode(img_bytes).decode('utf-8')
    
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe this image."},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_img}"}}
                ]
            }
        ]
    }

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient() as client:
        try:
            print(f"Testing {MODEL} vision...")
            resp = await client.post(f"{BASE_URL}/chat/completions", json=payload, headers=headers, timeout=10)
            print(f"Status: {resp.status_code}")
            print(resp.text)
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_vision())

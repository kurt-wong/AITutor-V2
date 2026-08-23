"""上传5科PDF（化学/生物/地理/历史/政治）。"""
import asyncio, aiohttp, json, sys, io, time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://localhost:8000"
PDF_DIR = Path(r"D:\Project\AITutors-v2\test\pdf")

SELECTED = [
    ("2026北京八一学校高一（上）期末化学（教师版）.pdf", "化学"),
    ("2026北京北师大附中高一（上）期末生物（教师版）.pdf", "生物"),
    ("2026北京朝阳高一（上）期末地理（教师版）.pdf", "地理"),
    ("2025北京东城高一（上）期末历史（教师版）.pdf", "历史"),
    ("2026北京东城高一（上）期末政治（教师版）.pdf", "政治"),
]


async def upload_pdf(session, filename, subject):
    pdf_path = PDF_DIR / filename
    data = aiohttp.FormData()
    f = open(pdf_path, 'rb')
    data.add_field('files', f, filename=filename, content_type='application/pdf')
    data.add_field('subject', subject)
    data.add_field('grade', '高一')
    async with session.post(f"{BASE_URL}/api/admin/documents/upload", data=data) as resp:
        result = await resp.json()
        f.close()
        if resp.status == 200:
            d = result.get('data', {})
            return d.get('document_ids', [None])[0], d.get('task_ids', [None])[0]
        print(f"  [ERROR] {resp.status}: {result}")
        return None, None


async def main():
    print(f"=== 5科 PDF 上传 ===\n")

    async with aiohttp.ClientSession() as session:
        for fn, subj in SELECTED:
            doc_id, task_id = await upload_pdf(session, fn, subj)
            if doc_id:
                print(f"↑ {subj} doc={doc_id[:8]} task={task_id[:8]}")
            else:
                print(f"✗ {subj} 上传失败")

    print(f"\n上传完成，等待管线处理...")

if __name__ == "__main__":
    asyncio.run(main())

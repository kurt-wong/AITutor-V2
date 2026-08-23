"""上传10份PDF（5科×2份）并监控管线执行。

选中的PDF：
- 数学：二中、朝阳
- 物理：八十中、朝阳
- 化学：八一学校、大兴
- 英语：房山、朝阳
- 语文：八十中、大兴
"""
import asyncio
import aiohttp
import json
import sys
import io
import os
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://localhost:8000"
PDF_DIR = Path(r"D:\Project\AITutors-v2\test\pdf")

# 选中的10份PDF：(文件名, 学科)
SELECTED_PDFS = [
    # 数学
    ("2026北京二中高一（上）期末数学（教师版）.pdf", "数学"),
    ("2026北京朝阳高一（上）期末数学（教师版）.pdf", "数学"),
    # 物理
    ("2026北京八十中高一（上）期末物理（教师版）.pdf", "物理"),
    ("2026北京朝阳高一（上）期末物理（教师版）.pdf", "物理"),
    # 化学
    ("2026北京八一学校高一（上）期末化学（教师版）.pdf", "化学"),
    ("2026北京大兴高一（上）期末化学（教师版）.pdf", "化学"),
    # 英语
    ("2026北京房山高一（上）期末英语（教师版）.pdf", "英语"),
    ("2026北京朝阳高一（上）期末英语（教师版）.pdf", "英语"),
    # 语文
    ("2026北京八十中高一（上）期末语文（教师版）.pdf", "语文"),
    ("2026北京大兴高一（上）期末语文（教师版）.pdf", "语文"),
]


async def upload_pdf(session, filename, subject):
    """上传单个PDF，返回 (document_id, task_id)。"""
    pdf_path = PDF_DIR / filename
    if not pdf_path.exists():
        print(f"  [ERROR] 文件不存在: {pdf_path}")
        return None, None

    data = aiohttp.FormData()
    data.add_field('files',
                   open(pdf_path, 'rb'),
                   filename=filename,
                   content_type='application/pdf')
    data.add_field('subject', subject)
    data.add_field('grade', '高一')

    async with session.post(f"{BASE_URL}/api/admin/documents/upload", data=data) as resp:
        result = await resp.json()
        if resp.status == 200:
            doc_ids = result.get('data', {}).get('document_ids', [])
            task_ids = result.get('data', {}).get('task_ids', [])
            return (doc_ids[0] if doc_ids else None,
                    task_ids[0] if task_ids else None)
        else:
            print(f"  [ERROR] 上传失败: {resp.status} {result}")
            return None, None


async def check_task_status(session, task_id):
    """查询任务状态。"""
    async with session.get(f"{BASE_URL}/api/admin/tasks/{task_id}") as resp:
        if resp.status == 200:
            result = await resp.json()
            return result.get('data', {})
        return None


async def check_document(session, doc_id):
    """查询文档状态。"""
    async with session.get(f"{BASE_URL}/api/admin/documents/{doc_id}") as resp:
        if resp.status == 200:
            result = await resp.json()
            return result.get('data', {})
        return None


async def monitor_pipeline(session, doc_id, task_id, filename, subject):
    """监控单个文档的管线执行，直到完成或超时。"""
    start = time.time()
    timeout = 600  # 10分钟超时

    while time.time() - start < timeout:
        # 检查任务状态
        task = await check_task_status(session, task_id)
        if task:
            status = task.get('status', 'unknown')
            result = task.get('result', {})

            if status in ('completed', 'failed'):
                elapsed = time.time() - start
                if status == 'completed':
                    q_count = result.get('total', result.get('ingested', '?'))
                    print(f"  [OK] {subject} {filename[:30]}... "
                          f"status={status} questions={q_count} "
                          f"elapsed={elapsed:.0f}s")
                else:
                    error = result.get('error', 'unknown')[:100]
                    print(f"  [FAIL] {subject} {filename[:30]}... "
                          f"status={status} error={error} "
                          f"elapsed={elapsed:.0f}s")
                return status, result

        await asyncio.sleep(10)  # 每10秒检查一次

    print(f"  [TIMEOUT] {subject} {filename[:30]}... 超过{timeout}s")
    return "timeout", {}


async def main():
    print(f"=== 全量 e2e 测试：5科×2份PDF ===")
    print(f"PDF目录: {PDF_DIR}")
    print(f"后端: {BASE_URL}")
    print()

    async with aiohttp.ClientSession() as session:
        # 1. 上传所有PDF
        print("=== 第1步：上传10份PDF ===")
        uploads = []  # (filename, subject, doc_id, task_id)

        for filename, subject in SELECTED_PDFS:
            doc_id, task_id = await upload_pdf(session, filename, subject)
            if doc_id:
                print(f"  [UPLOADED] {subject} {filename[:40]}... "
                      f"doc={doc_id[:8]} task={task_id[:8]}")
                uploads.append((filename, subject, doc_id, task_id))
            else:
                print(f"  [SKIP] {subject} {filename[:40]}... 上传失败")

        print(f"\n成功上传 {len(uploads)}/{len(SELECTED_PDFS)} 份")
        if not uploads:
            print("无上传文件，退出。")
            return

        # 2. 等待管线执行
        print(f"\n=== 第2步：监控管线执行（最长10分钟/份） ===")
        results = []

        # 并发监控所有文档
        tasks = []
        for filename, subject, doc_id, task_id in uploads:
            tasks.append(monitor_pipeline(session, doc_id, task_id, filename, subject))

        monitor_results = await asyncio.gather(*tasks, return_exceptions=True)

        # 3. 汇总结果
        print(f"\n=== 第3步：结果汇总 ===")
        success = 0
        failed = 0

        for i, (filename, subject, doc_id, task_id) in enumerate(uploads):
            if i < len(monitor_results) and not isinstance(monitor_results[i], Exception):
                status, result = monitor_results[i]
                if status == 'completed':
                    success += 1
                    q_count = result.get('total', result.get('ingested', '?'))
                    print(f"  ✅ {subject} | {filename[:50]} | {q_count}题")
                else:
                    failed += 1
                    print(f"  ❌ {subject} | {filename[:50]} | {status}")
            else:
                failed += 1
                print(f"  ❌ {subject} | {filename[:50]} | 异常")

        print(f"\n总计: {success} 成功, {failed} 失败, 共 {len(uploads)} 份")

        # 4. 最终DB状态
        print(f"\n=== 第4步：最终DB状态 ===")
        async with aiohttp.ClientSession() as s2:
            async with s2.get(f"{BASE_URL}/api/admin/statistics") as resp:
                if resp.status == 200:
                    stats = (await resp.json()).get('data', {})
                    print(f"  总题目数: {stats.get('total', '?')}")
                    qt_dist = stats.get('question_type_distribution', {})
                    for item in qt_dist:
                        print(f"    {item.get('question_type', '?')}: {item.get('count', '?')}")


if __name__ == "__main__":
    asyncio.run(main())

"""上传5份PDF（5科各1份）并监控管线执行。

选中的PDF（不在当前DB中）：
- 数学：八中
- 物理：昌平
- 化学：北师大二附中
- 英语：东城
- 语文：朝阳
"""
import asyncio
import aiohttp
import json
import sys
import io
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://localhost:8000"
PDF_DIR = Path(r"D:\Project\AITutors-v2\test\pdf")

SELECTED = [
    ("2026北京八中高一（上）期末数学（教师版）.pdf", "数学"),
    ("2026北京昌平高一（上）期末物理（教师版）.pdf", "物理"),
    ("2026北京北师大二附中高一（上）期末化学（教师版）.pdf", "化学"),
    ("2026北京东城高一（上）期末英语（教师版）.pdf", "英语"),
    ("2026北京朝阳高一（上）期末语文（教师版）.pdf", "语文"),
]


async def upload_pdf(session, filename, subject):
    pdf_path = PDF_DIR / filename
    data = aiohttp.FormData()
    # 使用 open(..., 'rb') 的 name 属性传原始文件名
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


async def wait_for_completion(session, doc_id, task_id, filename, subject, timeout=600):
    start = time.time()
    while time.time() - start < timeout:
        async with session.get(f"{BASE_URL}/api/admin/tasks/{task_id}") as resp:
            if resp.status == 200:
                data = (await resp.json()).get('data', {})
                status = data.get('status')
                if status in ('succeeded', 'failed'):
                    elapsed = time.time() - start
                    result = data.get('result', {})
                    if status == 'succeeded':
                        ing = result.get('ingestion', {})
                        q_count = ing.get('ingested', result.get('total', '?'))
                        print(f"  ✅ {subject} {filename[:35]}... {q_count}题 {elapsed:.0f}s")
                    else:
                        err = data.get('error_detail', '')[:80]
                        print(f"  ❌ {subject} {filename[:35]}... {err} {elapsed:.0f}s")
                    return status, result
        await asyncio.sleep(15)
    print(f"  ⏰ {subject} {filename[:35]}... 超时{timeout}s")
    return "timeout", {}


async def main():
    print(f"=== P0-A/P0-B 修复后验证：5科各1份PDF ===\n")

    async with aiohttp.ClientSession() as session:
        # 上传
        print("上传中...")
        uploads = []
        for fn, subj in SELECTED:
            doc_id, task_id = await upload_pdf(session, fn, subj)
            if doc_id:
                print(f"  ↑ {subj} {fn[:40]}... doc={doc_id[:8]}")
                uploads.append((fn, subj, doc_id, task_id))
            else:
                print(f"  ✗ {subj} {fn[:40]}... 上传失败")

        print(f"\n成功上传 {len(uploads)}/{len(SELECTED)}，等待管线...\n")

        # 并发监控
        tasks = [wait_for_completion(session, d, t, f, s) for f, s, d, t in uploads]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 汇总
        print(f"\n{'='*60}")
        print(f"  结果汇总")
        print(f"{'='*60}")

        success = 0
        total_q = 0
        for i, (fn, subj, doc_id, task_id) in enumerate(uploads):
            if i < len(results) and not isinstance(results[i], Exception):
                status, result = results[i]
                if status == 'succeeded':
                    success += 1
                    ing = result.get('ingestion', {})
                    q = ing.get('ingested', 0)
                    total_q += q
                    print(f"  ✅ {subj}: {q}题入库")
                else:
                    print(f"  ❌ {subj}: {status}")
            else:
                print(f"  ❌ {subj}: 异常")

        print(f"\n  总计: {success}/5 成功, {total_q} 题入库")

        # DB 验证
        print(f"\n{'='*60}")
        print(f"  DB 验证")
        print(f"{'='*60}")

        import asyncpg
        conn = await asyncpg.connect('postgresql://postgres:postgres@localhost:15432/aitutors')
        try:
            # 题型分布
            rows = await conn.fetch("""
                SELECT qt.code, COUNT(*) AS cnt
                FROM questions q
                LEFT JOIN question_types qt ON qt.id = q.question_type_id
                GROUP BY qt.code ORDER BY qt.code
            """)
            print(f"  题型分布:")
            for r in rows:
                print(f"    {r['code']}: {r['cnt']}")

            # 难度分布
            rows = await conn.fetch("""
                SELECT difficulty, COUNT(*) AS cnt
                FROM questions WHERE difficulty IS NOT NULL
                GROUP BY difficulty ORDER BY difficulty
            """)
            print(f"  难度分布:")
            for r in rows:
                print(f"    level {r['difficulty']}: {r['cnt']}")

            # NULL 检查
            null_type = await conn.fetchval("SELECT COUNT(*) FROM questions WHERE question_type_id IS NULL")
            null_diff = await conn.fetchval("SELECT COUNT(*) FROM questions WHERE difficulty IS NULL")
            print(f"  NULL题型: {null_type}, NULL难度: {null_diff}")

            # 按学科
            rows = await conn.fetch("""
                SELECT d.subject, COUNT(qi.id) AS questions
                FROM documents d
                LEFT JOIN question_instances qi ON qi.document_id = d.id
                WHERE d.processing_status = 'completed'
                GROUP BY d.subject ORDER BY d.subject
            """)
            print(f"  按学科:")
            for r in rows:
                print(f"    {r['subject']}: {r['questions']}题")

            # 失败文档
            rows = await conn.fetch("""
                SELECT subject, filename, processing_status, error_message
                FROM documents WHERE processing_status != 'completed'
            """)
            if rows:
                print(f"  失败文档:")
                for r in rows:
                    print(f"    {r['subject']} | {(r['error_message'] or '')[:60]}")

            # 总题目数
            total = await conn.fetchval("SELECT COUNT(*) FROM questions")
            print(f"\n  总题目数: {total}")
        finally:
            await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

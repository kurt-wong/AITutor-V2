"""上传语文+英语PDF，验证P0-G修复效果。"""
import asyncio, aiohttp, json, sys, io, time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://localhost:8000"
PDF_DIR = Path(r"D:\Project\AITutors-v2\test\pdf")

SELECTED = [
    ("2026北京朝阳高一（上）期末语文（教师版）.pdf", "语文"),
    ("2026北京东城高一（上）期末英语（教师版）.pdf", "英语"),
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
        return None, None


async def wait_for_completion(session, task_id, filename, subject, timeout=600):
    start = time.time()
    while time.time() - start < timeout:
        async with session.get(f"{BASE_URL}/api/admin/tasks/{task_id}") as resp:
            if resp.status == 200:
                data = (await resp.json()).get('data', {})
                status = data.get('status')
                if status in ('succeeded', 'failed'):
                    elapsed = time.time() - start
                    return status, data.get('result', {}), elapsed
        await asyncio.sleep(15)
    return "timeout", {}, timeout


async def main():
    print(f"=== P0-G 修复验证：语文+英语 PDF ===\n")

    async with aiohttp.ClientSession() as session:
        # 上传
        uploads = []
        for fn, subj in SELECTED:
            doc_id, task_id = await upload_pdf(session, fn, subj)
            if doc_id:
                print(f"↑ {subj} doc={doc_id[:8]} task={task_id[:8]}")
                uploads.append((fn, subj, doc_id, task_id))

        print(f"\n等待管线完成...\n")

        # 并发监控
        tasks = [wait_for_completion(session, t, f, s) for f, s, d, t in uploads]
        results = await asyncio.gather(*tasks)

        # 汇总
        print(f"{'='*60}")
        print(f"  管线结果")
        print(f"{'='*60}")
        for i, (fn, subj, doc_id, task_id) in enumerate(uploads):
            status, result, elapsed = results[i]
            if status == 'succeeded':
                ing = result.get('ingestion', {})
                print(f"  ✅ {subj}: ingested={ing.get('ingested',0)} skipped={ing.get('skipped',0)} failed={ing.get('failed',0)} {elapsed:.0f}s")
            else:
                print(f"  ❌ {subj}: {status} {elapsed:.0f}s")

        # DB 验证
        print(f"\n{'='*60}")
        print(f"  DB 验证")
        print(f"{'='*60}")

        import asyncpg
        conn = await asyncpg.connect('postgresql://postgres:postgres@localhost:15432/aitutors')
        try:
            # 按学科统计
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

            # 总题目数
            total = await conn.fetchval("SELECT COUNT(*) FROM questions")
            print(f"\n  总题目数: {total}")

            # 检查 composite 题的 stem 是否非空
            rows = await conn.fetch("""
                SELECT qi.source_question_number, q.is_composite, 
                       LENGTH(q.stem) as stem_len,
                       q.options IS NOT NULL as has_options,
                       q.sub_questions IS NOT NULL as has_subs
                FROM questions q
                JOIN question_instances qi ON qi.question_id = q.id
                JOIN documents d ON d.id = qi.document_id
                WHERE d.subject IN ('语文', '英语')
                ORDER BY d.subject, qi.source_question_number::int
            """)
            print(f"\n  逐题详情:")
            for r in rows:
                qn = r['source_question_number']
                comp = r['is_composite']
                stem_len = r['stem_len']
                has_opts = r['has_options']
                has_subs = r['has_subs']
                icon = "✅" if stem_len and stem_len > 0 else "❌"
                print(f"    {icon} Q{qn} | composite={comp} | stem_len={stem_len} | options={has_opts} | subs={has_subs}")

            # 检查失败文档
            rows = await conn.fetch("""
                SELECT subject, processing_status, error_message
                FROM documents WHERE processing_status != 'completed'
            """)
            if rows:
                print(f"\n  失败文档:")
                for r in rows:
                    print(f"    {r['subject']} | {r['processing_status']} | {(r['error_message'] or '')[:60]}")

        finally:
            await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

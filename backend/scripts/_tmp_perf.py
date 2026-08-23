"""查明管线效率：每份文档的处理时间、阶段耗时、重试情况。"""
import asyncio, asyncpg, sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"

async def main():
    conn = await asyncpg.connect(DSN)
    try:
        # 任务时间线
        rows = await conn.fetch("""
            SELECT bt.id, bt.status, bt.current_stage, bt.progress,
                   bt.created_at, bt.updated_at,
                   bt.result_json::text as result,
                   d.subject, d.filename
            FROM background_tasks bt
            JOIN documents d ON d.id::text = bt.payload_json->>'document_id'
            ORDER BY bt.created_at
        """)
        print(f"=== 任务时间线（{len(rows)}） ===\n")
        for r in rows:
            subj = r['subject'] or '?'
            created = r['created_at']
            updated = r['updated_at']
            duration = (updated - created).total_seconds() if updated and created else 0
            minutes = duration / 60

            # 解析 result_json 中的阶段耗时
            stages_info = ""
            result = r['result']
            if result:
                try:
                    data = json.loads(result)
                    stages = data.get('stages', [])
                    if stages:
                        stage_parts = []
                        for s in stages:
                            name = s.get('name', '?')
                            ms = s.get('duration_ms', 0)
                            stage_parts.append(f"{name}:{ms/1000:.0f}s")
                        stages_info = " | ".join(stage_parts)
                    total_ms = data.get('total_time_ms', 0)
                    if total_ms:
                        stages_info += f" [total:{total_ms/1000:.0f}s]"
                except:
                    pass

            print(f"  {subj:4s} | {r['status']:10s} | {minutes:6.1f}min | {created.strftime('%H:%M')} → {updated.strftime('%H:%M')}")
            if stages_info:
                print(f"       stages: {stages_info}")

        # 检查是否有重试
        print(f"\n=== 文档处理日志（最近 30 条） ===")
        logs = await conn.fetch("""
            SELECT d.subject, dpl.stage, dpl.message, dpl.created_at
            FROM document_processing_logs dpl
            JOIN documents d ON d.id = dpl.document_id
            ORDER BY dpl.created_at DESC LIMIT 30
        """)
        for l in logs:
            subj = l['subject'] or '?'
            msg = (l['message'] or '')[:80]
            print(f"  {l['created_at'].strftime('%H:%M:%S')} | {subj:4s} | {l['stage']:20s} | {msg}")

        # 检查 LLM 超时配置
        print(f"\n=== LLM 配置 ===")
        print(f"  LLM_REQUEST_TIMEOUT_SECONDS: 300 (from .env)")
        print(f"  PADDLEOCR_JOB_TIMEOUT_SECONDS: 600 (from .env)")

    finally:
        await conn.close()

asyncio.run(main())

import asyncio, asyncpg, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
async def main():
    conn = await asyncpg.connect('postgresql://postgres:postgres@localhost:15432/aitutors')
    try:
        cols = await conn.fetch("""
            SELECT column_name, data_type FROM information_schema.columns
            WHERE table_name = 'background_tasks' ORDER BY ordinal_position
        """)
        print('background_tasks columns:')
        for c in cols:
            print(f"  {c['column_name']:25s} {c['data_type']}")

        rows = await conn.fetch("SELECT id, status, task_type, result_json FROM background_tasks ORDER BY created_at")
        print(f"\n=== tasks ({len(rows)}) ===")
        for r in rows:
            result = (r['result_json'] or '')[:150]
            print(f"  {r['task_type']:15s} | {r['status']:10s} | {result}")

        # Check worker
        rows2 = await conn.fetch("SELECT COUNT(*) as cnt, processing_status FROM documents GROUP BY processing_status")
        print("\n=== doc status ===")
        for r in rows2:
            print(f"  {r['processing_status']}: {r['cnt']}")

        qcnt = await conn.fetchval("SELECT COUNT(*) FROM questions")
        print(f"\nquestions: {qcnt}")
    finally:
        await conn.close()
asyncio.run(main())

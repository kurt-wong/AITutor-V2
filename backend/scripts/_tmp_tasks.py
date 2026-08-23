import asyncio, asyncpg, sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"
async def main():
    conn = await asyncpg.connect(DSN)
    try:
        rows = await conn.fetch("""
            SELECT id, status, current_stage, progress, error_detail
            FROM background_tasks ORDER BY created_at
        """)
        print(f"=== tasks ({len(rows)}) ===")
        for r in rows:
            print(f"  {r['status']:10s} | stage={r['current_stage'] or '':20s} | progress={r['progress']} | err={str(r['error_detail'] or '')[:60]}")
    finally:
        await conn.close()
asyncio.run(main())

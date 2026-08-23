"""Step 0: 数据库验证脚本 — 执行 PHASE_2A_EXECUTION_PLAN.md 要求的所有 SQL 查询。"""
import asyncio
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings

sys.stdout.reconfigure(encoding='utf-8')


async def verify():
    engine = create_async_engine(settings.database_url)
    async with engine.connect() as conn:

        # ── 1. 列验证 ──────────────────────────────────────────────
        print("=" * 60)
        print("1. 列验证 (questions / question_instances / question_knowledge)")
        print("=" * 60)
        r = await conn.execute(text("""
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_name IN ('questions', 'question_instances', 'question_knowledge')
            ORDER BY table_name, column_name
        """))
        rows = list(r)
        current_table = None
        for row in rows:
            if row[0] != current_table:
                current_table = row[0]
                print(f"\n  [{current_table}]")
            print(f"    {row[1]}")

        # ── 2. 索引验证 ──────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("2. 索引验证 (question_instances)")
        print("=" * 60)
        r = await conn.execute(text("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'question_instances'
              AND indexname = 'ix_question_instances_doc_qno'
        """))
        rows = list(r)
        if rows:
            print(f"  [OK] {rows[0][0]}")
            print(f"  {rows[0][1]}")
        else:
            print("  [FAIL] ix_question_instances_doc_qno NOT FOUND")

        await conn.commit()

        # ── 3. document_id NULL 检查 ────────────────────────────────
        print("\n" + "=" * 60)
        print("3. document 来源 Instance 的 document_id NULL 检查")
        print("=" * 60)
        r = await conn.execute(text("""
            SELECT count(*)
            FROM question_instances
            WHERE source_type = 'document'
              AND document_id IS NULL
        """))
        null_count = r.scalar()
        print(f"  document-sourced instances with NULL document_id: {null_count}")
        if null_count == 0:
            print("  [OK]")
        else:
            print(f"  [FAIL] {null_count} instances have NULL document_id")

        # ── 4. 唯一约束重复检查 ──────────────────────────────────────
        print("\n" + "=" * 60)
        print("4. 唯一约束重复检查")
        print("=" * 60)
        r = await conn.execute(text("""
            SELECT count(*)
            FROM question_instances
            WHERE source_type = 'document'
              AND source_question_number IS NOT NULL
            GROUP BY document_id, source_question_number
            HAVING count(*) > 1
        """))
        dupes = list(r)
        if not dupes:
            print("  [OK] No duplicate (document_id, source_question_number)")
        else:
            print(f"  [FAIL] Found {len(dupes)} duplicate groups")

        await conn.commit()

        # ── 5. questions.year/school 残留检查 ────────────────────────
        print("\n" + "=" * 60)
        print("5. questions.year/school 残留检查")
        print("=" * 60)
        try:
            r = await conn.execute(text("""
                SELECT count(*)
                FROM questions
                WHERE year IS NOT NULL OR school IS NOT NULL
            """))
            count = r.scalar()
            print(f"  [WARN] questions.year/school columns still exist, {count} rows have values")
            await conn.commit()
        except Exception:
            await conn.rollback()
            print("  [OK] questions.year/school columns do not exist (correctly dropped)")

        # ── 6. 数据统计 ──────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("6. 数据统计")
        print("=" * 60)
        r = await conn.execute(text("SELECT COUNT(*) FROM documents"))
        print(f"  documents: {r.scalar()}")
        r = await conn.execute(text("SELECT COUNT(*) FROM questions"))
        print(f"  questions: {r.scalar()}")
        r = await conn.execute(text("SELECT COUNT(*) FROM question_instances"))
        print(f"  question_instances: {r.scalar()}")
        r = await conn.execute(text("SELECT COUNT(*) FROM question_knowledge"))
        print(f"  question_knowledge: {r.scalar()}")

        await conn.commit()

    await engine.dispose()
    print("\n" + "=" * 60)
    print("DONE: All Step 0 database verifications completed.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(verify())

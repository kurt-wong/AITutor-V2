"""验证 Phase 2A migration 执行结果。"""
import asyncio
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings

# Force UTF-8 output on Windows
sys.stdout.reconfigure(encoding='utf-8')


async def verify():
    engine = create_async_engine(settings.database_url)
    async with engine.connect() as conn:
        # 1. questions 表：year/school 已移除，content_hash 已添加
        r = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='questions' AND column_name IN ('year','school','content_hash') "
            "ORDER BY column_name"
        ))
        cols = [row[0] for row in r]
        assert "content_hash" in cols, f"content_hash missing: {cols}"
        assert "year" not in cols, f"year still exists: {cols}"
        assert "school" not in cols, f"school still exists: {cols}"
        print(f"[OK] questions: year/school removed, content_hash added ({cols})")

        # 2. question_instances.document_id: NOT NULL
        r = await conn.execute(text(
            "SELECT column_name, is_nullable FROM information_schema.columns "
            "WHERE table_name='question_instances' AND column_name='document_id'"
        ))
        row = r.fetchone()
        assert row is not None, "document_id column missing"
        assert row[1] == "NO", f"document_id should be NOT NULL, got nullable={row[1]}"
        print(f"[OK] question_instances.document_id: NOT NULL")

        # 3. question_knowledge: mapping_source/review_status
        r = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='question_knowledge' AND column_name IN ('mapping_source','review_status') "
            "ORDER BY column_name"
        ))
        cols = [row[0] for row in r]
        assert "mapping_source" in cols, f"mapping_source missing: {cols}"
        assert "review_status" in cols, f"review_status missing: {cols}"
        print(f"[OK] question_knowledge: mapping_source/review_status added ({cols})")

        # 4. 索引验证
        r = await conn.execute(text(
            "SELECT indexname FROM pg_indexes "
            "WHERE tablename='questions' AND indexname LIKE 'ix_questions%' "
            "ORDER BY indexname"
        ))
        idxs = [row[0] for row in r]
        assert "ix_questions_subject_grade" in idxs, f"ix_questions_subject_grade missing: {idxs}"
        assert "ix_questions_subject_grade_year" not in idxs, f"old index still exists: {idxs}"
        assert "ix_questions_content_hash" in idxs, f"ix_questions_content_hash missing: {idxs}"
        print(f"[OK] questions indexes: {idxs}")

        r = await conn.execute(text(
            "SELECT indexname FROM pg_indexes "
            "WHERE tablename='question_instances' AND indexname LIKE 'ix_question%' "
            "ORDER BY indexname"
        ))
        idxs = [row[0] for row in r]
        assert "ix_question_instances_doc_qno" in idxs, f"ix_question_instances_doc_qno missing: {idxs}"
        print(f"[OK] question_instances indexes: {idxs}")

        # 5. 数据统计
        r = await conn.execute(text("SELECT COUNT(*) FROM documents"))
        docs = r.scalar()
        r = await conn.execute(text("SELECT COUNT(*) FROM question_instances"))
        insts = r.scalar()
        r = await conn.execute(text("SELECT COUNT(*) FROM questions"))
        qs = r.scalar()
        print(f"[DATA] documents={docs}, questions={qs}, question_instances={insts}")

        # 6. document_id 回填验证（如果有 instances）
        if insts > 0:
            r = await conn.execute(text(
                "SELECT COUNT(*) FROM question_instances WHERE document_id IS NULL"
            ))
            null_count = r.scalar()
            assert null_count == 0, f"{null_count} instances still have NULL document_id"
            print(f"[OK] All {insts} instances have non-NULL document_id")
        else:
            print("[INFO] No question_instances to verify backfill")

        # 7. year/school 迁移验证
        if insts > 0:
            r = await conn.execute(text(
                "SELECT year, school FROM question_instances LIMIT 5"
            ))
            rows = [(row[0], row[1]) for row in r]
            print(f"[DATA] Sample instance year/school: {rows}")

    await engine.dispose()
    print("\n[DONE] All migration verifications passed!")


if __name__ == "__main__":
    asyncio.run(verify())

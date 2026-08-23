#!/usr/bin/env python3
"""对抗性审查：检查英语 L2 标注中 composite 题目的 stem_line_ids 与 shared_material_line_ids 关系。"""
import asyncio
import json
import sys
import io

if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"

async def main():
    import asyncpg
    conn = await asyncpg.connect(DSN)
    try:
        doc = await conn.fetchrow(
            "SELECT id, filename, llm_annotated_markdown "
            "FROM documents WHERE subject='英语' AND processing_status='completed' "
            "ORDER BY created_at DESC LIMIT 1"
        )
        if not doc:
            print("No English doc found")
            return

        l2_raw = doc["llm_annotated_markdown"] or "{}"
        try:
            l2_data = json.loads(l2_raw)
        except:
            print("Failed to parse L2 data")
            return

        questions = l2_data.get("questions", [])
        print(f"English L2: {len(questions)} questions")

        for q in questions:
            qno = q.get("question_number", "?")
            is_comp = q.get("is_composite", False)
            stem_ids = q.get("stem_line_ids", [])
            mat_ids = q.get("shared_material_line_ids", [])

            if not is_comp:
                continue

            stem_set = set(stem_ids)
            mat_set = set(mat_ids)
            overlap = stem_set & mat_set
            mat_only = mat_set - stem_set
            stem_only = stem_set - mat_set

            print(f"\nQ{qno}: composite={is_comp}")
            print(f"  stem_line_ids: {len(stem_ids)} lines")
            print(f"  shared_material_line_ids: {len(mat_ids)} lines")
            print(f"  overlap: {len(overlap)}")
            print(f"  material-only (NOT in stem): {len(mat_only)}")
            print(f"  stem-only (NOT material): {len(stem_only)}")

            if mat_only:
                print(f"  *** MATERIAL LOSS: {len(mat_only)} material lines NOT in stem_line_ids ***")
                # Show first few material-only line IDs
                for lid in list(mat_only)[:3]:
                    print(f"    - {lid}")

            # Also check the actual stem content from DB
            db_row = await conn.fetchrow(
                """
                SELECT q.stem, q.options
                FROM questions q
                JOIN question_instances qi ON qi.question_id = q.id
                WHERE qi.document_id = $1 AND qi.source_question_number = $2
                """,
                str(doc["id"]), str(qno),
            )
            if db_row:
                db_stem = db_row["stem"] or ""
                print(f"  DB stem length: {len(db_stem)} chars")
                # Check if material content is in DB stem
                # Look for typical material markers
                if len(mat_ids) > 0 and len(db_stem) < 100:
                    print(f"  *** SUSPICIOUS: stem is very short ({len(db_stem)} chars) despite having {len(mat_ids)} material lines ***")

    finally:
        await conn.close()

asyncio.run(main())

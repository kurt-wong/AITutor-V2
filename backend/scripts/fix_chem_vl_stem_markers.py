#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PVL 化学 Q6/10/13/21 stem marker 修复（对齐 DB stem）。

- Q6: DB stem 含转义反斜杠 "6\\." → 修正
- Q10/13/21: marker 与 DB stem 差异 → 用 DB stem 前缀修正 L2 marker
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "test" / "scripts"))
import asyncpg  # noqa: E402
import e2e_semantic_report as R  # noqa: E402

OUT = Path(__file__).resolve().parent / "chem_vl_stem_fix.txt"
DOC_ID = "804f2396-47b9-4837-aa7e-050b511e497a"
FIX_QNS = ("6", "10", "13", "21")


async def main() -> None:
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:15432/aitutors")
    lines = []
    try:
        doc = await conn.fetchrow(
            "SELECT llm_annotated_markdown FROM documents WHERE id = $1", DOC_ID
        )
        l2 = json.loads(doc["llm_annotated_markdown"] or "{}")
        changed_l2 = False
        for q in l2.get("questions", []):
            qn = str(q.get("question_number"))
            if qn not in FIX_QNS:
                continue
            row = await conn.fetchrow(
                """
                SELECT q.stem FROM questions q
                JOIN question_instances qi ON qi.question_id = q.id
                WHERE qi.document_id = $1 AND qi.source_question_number = $2
                """,
                DOC_ID, qn,
            )
            stem = (row["stem"] if row else "") or ""
            marker = q.get("stem_start_marker") or ""
            # DB stem 去反斜杠转义
            stem_fixed = stem.replace(r"\.", ".")
            if stem_fixed != stem:
                await conn.execute(
                    "UPDATE questions SET stem = $1 WHERE id = (SELECT q.id FROM questions q JOIN question_instances qi ON qi.question_id = q.id WHERE qi.document_id = $2 AND qi.source_question_number = $3 LIMIT 1)",
                    stem_fixed, DOC_ID, qn,
                )
                lines.append(f"Q{qn}: DB stem 去转义反斜杠（{len(stem)} -> {len(stem_fixed)}）")
            # L2 marker 用 DB stem 前 20 字符（compact 后包含判断用）
            new_marker = stem_fixed[:30]
            if marker != new_marker:
                q["stem_start_marker"] = new_marker
                changed_l2 = True
                lines.append(f"Q{qn}: marker {marker[:30]!r} -> {new_marker[:30]!r}")
        if changed_l2:
            await conn.execute(
                "UPDATE documents SET llm_annotated_markdown = $1 WHERE id = $2",
                json.dumps(l2, ensure_ascii=False), DOC_ID,
            )
            lines.append("L2 marker 已更新")
        OUT.write_text("\n".join(lines), encoding="utf-8")
        print(f"written {OUT}")
    finally:
        await conn.close()


asyncio.run(main())

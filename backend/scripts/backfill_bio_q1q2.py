#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据修复：生物 Q1/Q2 缺库回填（stem 为空被丢弃，源与选项答案齐全）。"""
import asyncio
import hashlib
import json
import re
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "test" / "scripts"))
import asyncpg  # noqa: E402
import e2e_semantic_report as R  # noqa: E402

DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"
SINGLE_CHOICE = "59e1cfb6-ee60-4cfe-a4ed-69c7b9d784eb"

# 从源提取的题干（pdf_raw）
Q1_STEM_START = "1.病毒、细菌、真菌以及一些小型的原生生物构成的生物群体"
Q1_STEM_END = "以下关于微生物的说法正确的是（）"
Q2_STEM_START = "2.下列有关细胞中元素和化合物的叙述正确的是（）"


async def _hash(stem: str, options) -> str:
    return hashlib.sha256(
        json.dumps({
            "stem": re.sub(r"\s+", "", stem),
            "options": [
                {"label": o.get("label"), "text": re.sub(r"\s+", "", o.get("text", ""))}
                for o in (options or [])
            ],
            "question_type": "single_choice",
        }, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


async def main() -> None:
    conn = await asyncpg.connect(DSN)
    try:
        doc = await conn.fetchrow(
            "SELECT id, filename, grade, year, school FROM documents WHERE subject='生物' AND processing_status='completed' ORDER BY created_at DESC LIMIT 1"
        )
        doc_id = str(doc["id"])
        subj = await conn.fetchrow("SELECT id FROM subjects WHERE name = '生物'")
        subject_id = str(subj["id"])
        raw = R._extract_pdf_raw_text("生物", doc["filename"] or "")
        stripped = re.sub(r"\s+", "", raw)

        task = await conn.fetchrow(
            """
            SELECT result_json FROM background_tasks
            WHERE payload_json->>'document_id' = $1 ORDER BY created_at DESC LIMIT 1
            """,
            doc_id,
        )
        res = json.loads(task["result_json"] or "{}") if task else {}
        pipe_qs = {str(q.get("question_number")): q for q in res.get("questions", []) if isinstance(q, dict)}

        for qn, start_m, end_m in [("1", Q1_STEM_START, Q1_STEM_END), ("2", Q2_STEM_START, None)]:
            exists = await conn.fetchval(
                """
                SELECT 1 FROM question_instances qi JOIN questions q ON q.id = qi.question_id
                WHERE qi.document_id = $1 AND qi.source_question_number = $2
                """,
                doc_id, qn,
            )
            if exists:
                print(f"Q{qn}: 已存在，跳过")
                continue
            s_pos = stripped.find(start_m)
            if s_pos < 0:
                print(f"Q{qn}: 源题干未找到")
                continue
            if end_m:
                e_pos = stripped.find(end_m, s_pos)
                stem = stripped[s_pos : e_pos + len(end_m)] if e_pos >= 0 else stripped[s_pos : s_pos + 200]
            else:
                # Q2：到下一题号（3.）前
                nxt = stripped.find("3.", s_pos + 2)
                stem = stripped[s_pos:nxt] if nxt >= 0 else stripped[s_pos : s_pos + 200]
            pq = pipe_qs.get(qn) or {}
            options = pq.get("options") or []
            answer = (pq.get("answer") or "").strip()
            if not options or not answer:
                print(f"Q{qn}: 管线 options/answer 缺失")
                continue
            print(f"Q{qn} stem ({len(stem)}): {stem[:60]}...  answer={answer}")
            content_hash = await _hash(stem, options)
            existing_qid = await conn.fetchval(
                "SELECT id FROM questions WHERE content_hash = $1 AND subject_id = $2",
                content_hash, subject_id,
            )
            qid = existing_qid
            if not qid:
                qid = str(uuid.uuid4())
                await conn.execute(
                    """
                    INSERT INTO questions
                      (id, subject_id, grade, question_type_id, score, difficulty, stem, options,
                       answer, explanation, source_type, source_document_name, status, confidence,
                       occurrence_count, created_at, updated_at, is_composite, sub_questions,
                       review_reason, content_hash)
                    VALUES ($1, $2, $3, $4, NULL, NULL, $5, $6::jsonb, $7, NULL, 'document', $8,
                            'approved', 0.95, 1, now(), now(), false, NULL, NULL, $9)
                    """,
                    qid, subject_id, doc["grade"], SINGLE_CHOICE,
                    stem, json.dumps(options, ensure_ascii=False), answer,
                    doc["filename"], content_hash,
                )
            inst_id = str(uuid.uuid4())
            await conn.execute(
                """
                INSERT INTO question_instances
                  (id, question_id, source_type, source_document_name, source_page,
                   source_question_number, year, school, occurrence_no, created_at, document_id)
                VALUES ($1, $2, 'document', $3, 1, $4, $5, $6, 1, now(), $7)
                """,
                inst_id, qid, doc["filename"], qn, doc["year"], doc["school"], doc_id,
            )
            await conn.execute(
                "UPDATE questions SET occurrence_count = (SELECT count(*) FROM question_instances WHERE question_id = $1) WHERE id = $1",
                qid,
            )
            print(f"Q{qn}: 已回填")
    finally:
        await conn.close()


asyncio.run(main())

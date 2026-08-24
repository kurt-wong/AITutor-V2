#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据修复：历史 PPS 版 Q37 缺库回填。

PPS 重跑时 LLM 标注 Q37 "锚点需重新标注/题干为空" 被丢弃。源数据完整
（pdf_raw 题干 + 管线选项 + 答案区 37.【答案】A）。从源提取回填，
幂等：该文档该题号已存在则跳过。
"""
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
SINGLE_CHOICE_TYPE = "59e1cfb6-ee60-4cfe-a4ed-69c7b9d784eb"

STEM_START = "中国共产党成立以来"
OPTIONS_START = "①②④③"


async def main() -> None:
    conn = await asyncpg.connect(DSN)
    try:
        doc = await conn.fetchrow(
            "SELECT id, filename, grade, year, school FROM documents WHERE subject='历史' AND processing_status='completed' ORDER BY created_at DESC LIMIT 1"
        )
        doc_id = str(doc["id"])
        raw = R._extract_pdf_raw_text("历史", doc["filename"] or "")
        stripped = re.sub(r"\s+", "", raw)

        # 幂等
        exists = await conn.fetchval(
            """
            SELECT 1 FROM question_instances qi JOIN questions q ON q.id = qi.question_id
            WHERE qi.document_id = $1 AND qi.source_question_number = '37'
            """,
            doc_id,
        )
        if exists:
            print("Q37: 已存在，跳过")
            return

        # 题干：STEM_START 到 OPTIONS_START 前
        s_pos = stripped.find(STEM_START)
        if s_pos < 0:
            print("未找到 Q37 题干起点")
            return
        o_pos = stripped.find(OPTIONS_START, s_pos)
        if o_pos < 0:
            print("未找到选项起点")
            return
        stem = stripped[s_pos:o_pos].rstrip()
        print(f"stem ({len(stem)} 字符): {stem[:80]}...")

        # 选项（管线任务里有）
        task = await conn.fetchrow(
            """
            SELECT result_json FROM background_tasks
            WHERE payload_json->>'document_id' = $1 ORDER BY created_at DESC LIMIT 1
            """,
            doc_id,
        )
        res = json.loads(task["result_json"] or "{}") if task else {}
        q37 = next((q for q in res.get("questions", []) if str(q.get("question_number")) == "37"), None)
        if not q37 or not q37.get("options"):
            print("管线无 Q37 options")
            return
        options = q37["options"]

        subj = await conn.fetchrow("SELECT id FROM subjects WHERE name = '历史'")
        content_hash = hashlib.sha256(
            json.dumps({
                "stem": re.sub(r"\s+", "", stem),
                "options": [{"label": o.get("label"), "text": re.sub(r"\s+", "", o.get("text", ""))} for o in options],
                "question_type": "single_choice",
            }, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        existing_qid = await conn.fetchval(
            "SELECT id FROM questions WHERE content_hash = $1 AND subject_id = $2",
            content_hash, str(subj["id"]),
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
                VALUES ($1, $2, $3, $4, NULL, NULL, $5, $6::jsonb, 'A', NULL, 'document', $7,
                        'approved', 0.95, 1, now(), now(), false, NULL, NULL, $8)
                """,
                qid, str(subj["id"]), doc["grade"], SINGLE_CHOICE_TYPE,
                stem, json.dumps(options, ensure_ascii=False), doc["filename"], content_hash,
            )
            print(f"Q37: 新建 Question {str(qid)[:8]}")
        inst_id = str(uuid.uuid4())
        await conn.execute(
            """
            INSERT INTO question_instances
              (id, question_id, source_type, source_document_name, source_page,
               source_question_number, year, school, occurrence_no, created_at, document_id)
            VALUES ($1, $2, 'document', $3, 9, '37', $4, $5, 1, now(), $6)
            """,
            inst_id, qid, doc["filename"], doc["year"], doc["school"], doc_id,
        )
        await conn.execute(
            "UPDATE questions SET occurrence_count = (SELECT count(*) FROM question_instances WHERE question_id = $1) WHERE id = $1",
            qid,
        )
        print(f"Q37: 已回填（question={str(qid)[:8]}, instance={str(inst_id)[:8]}, answer=A）")
    finally:
        await conn.close()


asyncio.run(main())

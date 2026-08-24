#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据修复：地理缺库——Q21/Q30 回填 + L2 幻觉题 Q23/Q24/Q25 删除。

2026-08-25 诊断结论：
- 源试卷题号序列为 1-22（选择）+ 26-30（非选择），**不存在 Q23/Q24/Q25**；
  L2 幻造 3 题（把材料正文当题干），DB 因此 L2 30 vs DB 25。
- Q21/Q30 源中有真实内容但 LLM 标注失败（stem 空）被丢弃。
处理：L2 删除幻觉题；Q21 回填（stem/options/answer=C）；Q30 回填 stem
（answer 管线已有）。幂等：已存在则跳过。
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
SINGLE_CHOICE = "59e1cfb6-ee60-4cfe-a4ed-69c7b9d784eb"
SHORT_ANSWER = "07d11bf8-1e7e-457e-bcbb-24b43adf04cf"
HALLUCINATED = {"23", "24", "25"}

# Q21 数据（源提取）
Q21_STEM = "21.与图(b)相比，图(a)所示土壤剖面（）"
Q21_OPTIONS = [
    {"label": "A", "text": "土层数量更多"},
    {"label": "B", "text": "有机层缺失"},
    {"label": "C", "text": "腐殖质层更厚"},
    {"label": "D", "text": "淀积层分布更浅"},
]
Q21_ANSWER = "C"


def _hash(stem: str, options, qtype: str) -> str:
    return hashlib.sha256(
        json.dumps({
            "stem": re.sub(r"\s+", "", stem),
            "options": [
                {"label": o.get("label"), "text": re.sub(r"\s+", "", o.get("text", ""))}
                for o in (options or [])
            ],
            "question_type": qtype,
        }, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


async def _insert(conn, doc, subject_id, qn: str, stem: str, options, answer: str, qtype_id: str, page: int):
    content_hash = _hash(stem, options, "single_choice" if qtype_id == SINGLE_CHOICE else "short_answer")
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
            qid, subject_id, doc["grade"], qtype_id,
            stem, json.dumps(options or [], ensure_ascii=False), answer,
            doc["filename"], content_hash,
        )
    inst_id = str(uuid.uuid4())
    await conn.execute(
        """
        INSERT INTO question_instances
          (id, question_id, source_type, source_document_name, source_page,
           source_question_number, year, school, occurrence_no, created_at, document_id)
        VALUES ($1, $2, 'document', $3, $4, $5, $6, $7, 1, now(), $8)
        """,
        inst_id, qid, doc["filename"], page, qn, doc["year"], doc["school"], str(doc["id"]),
    )
    await conn.execute(
        "UPDATE questions SET occurrence_count = (SELECT count(*) FROM question_instances WHERE question_id = $1) WHERE id = $1",
        qid,
    )
    return qid


async def main() -> None:
    conn = await asyncpg.connect(DSN)
    try:
        doc = await conn.fetchrow(
            "SELECT id, filename, grade, year, school, llm_annotated_markdown FROM documents WHERE subject='地理' AND processing_status='completed' ORDER BY created_at DESC LIMIT 1"
        )
        doc_id = str(doc["id"])
        subj = await conn.fetchrow("SELECT id FROM subjects WHERE name = '地理'")
        subject_id = str(subj["id"])

        # 1. L2 删幻觉题
        l2 = json.loads(doc["llm_annotated_markdown"] or "{}")
        before = len(l2.get("questions", []))
        l2["questions"] = [q for q in l2.get("questions", []) if str(q.get("question_number")) not in HALLUCINATED]
        after = len(l2["questions"])
        if after != before:
            await conn.execute(
                "UPDATE documents SET llm_annotated_markdown = $1 WHERE id = $2",
                json.dumps(l2, ensure_ascii=False), doc_id,
            )
            print(f"L2 删除幻觉题: {before} -> {after}")

        # 2. Q21 回填
        exists = await conn.fetchval(
            """
            SELECT 1 FROM question_instances qi JOIN questions q ON q.id = qi.question_id
            WHERE qi.document_id = $1 AND qi.source_question_number = '21'
            """,
            doc_id,
        )
        if not exists:
            await _insert(conn, doc, subject_id, "21", Q21_STEM, Q21_OPTIONS, Q21_ANSWER, SINGLE_CHOICE, 6)
            print("Q21 已回填")
        else:
            print("Q21 已存在")

        # 3. Q30 stem 回填（answer 从管线）
        task = await conn.fetchrow(
            """
            SELECT result_json FROM background_tasks
            WHERE payload_json->>'document_id' = $1 ORDER BY created_at DESC LIMIT 1
            """,
            doc_id,
        )
        res = json.loads(task["result_json"] or "{}") if task else {}
        q30 = next((q for q in res.get("questions", []) if str(q.get("question_number")) == "30"), None)
        q30_answer = (q30 or {}).get("answer") or ""
        exists30 = await conn.fetchval(
            """
            SELECT 1 FROM question_instances qi JOIN questions q ON q.id = qi.question_id
            WHERE qi.document_id = $1 AND qi.source_question_number = '30'
            """,
            doc_id,
        )
        if not exists30:
            raw = R._extract_pdf_raw_text("地理", doc["filename"] or "")
            stripped = "".join(raw.split())
            s_pos = stripped.find("30.某地理小组开展防灾减灾实验探究活动")
            if s_pos < 0:
                print("Q30 源题干未找到")
            else:
                # 题干到下一题号/答案区
                seg = stripped[s_pos:]
                nxt = re.search(r"31[.．]|参考答案", seg[10:])
                stem30 = seg[: nxt.start() + 10] if nxt else seg[:2000]
                await _insert(conn, doc, subject_id, "30", stem30, [], q30_answer, SHORT_ANSWER, 13)
                print(f"Q30 已回填（stem {len(stem30)} 字符, answer {len(q30_answer)} 字符）")
        else:
            print("Q30 已存在")
    finally:
        await conn.close()


asyncio.run(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据修复：物理 Q4/Q7 缺库回填（自主命制试题部分，用户按序修复任务①）。

根因：正文第2页仅 "4.(集团校自创题)"/"7.(集团校自创题)" 占位标记，
真实题干+选项在第9页"自主命制试题"部分；管线 LLM 提取了选项但题干为空 →
ingestion 丢弃。答案在答案区"自主命制试题答案 4. A / 7. B"。

本脚本从 pdf_raw 程序化提取题干，复用管线选项与答案，幂等插入
Question + QuestionInstance（物理最新 completed 文档）。
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

# 题干提取：起点标记 → 终点标记（对 pdf_raw 去空白后的连续文本匹配，
# 原文为逐字符换行 + 全角标点，raw.find 不可靠）
Q4_START = "4.某景区的滑沙项目深受游客喜爱"
Q4_END = "下列说法正确的是()"
Q7_START = "7.2025年4月24日，长征二号F运载火箭搭载神舟二十号载人飞船成功发射升空"
Q7_END = "下列说法中正确的是()"


def extract_stem(source: str, start_marker: str, end_marker: str) -> str | None:
    pos = source.find(start_marker)
    if pos < 0:
        return None
    end = source.find(end_marker, pos)
    if end < 0:
        return None
    return source[pos : end + len(end_marker)]


def compute_hash(stem: str, options: list[dict]) -> str:
    payload = json.dumps(
        {
            "stem": re.sub(r"\s+", "", stem or ""),
            "options": [
                {"label": o.get("label"), "text": re.sub(r"\s+", "", o.get("text", ""))}
                for o in (options or [])
            ],
            "question_type": "single_choice",
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


async def main() -> None:
    conn = await asyncpg.connect(DSN)
    try:
        doc = await conn.fetchrow(
            """
            SELECT id, filename, subject, grade, year, school, llm_annotated_markdown
            FROM documents
            WHERE subject = '物理' AND processing_status = 'completed'
            ORDER BY created_at DESC LIMIT 1
            """
        )
        doc_meta = doc
        doc_id = str(doc["id"])
        raw = R._extract_pdf_raw_text("物理", doc["filename"] or "")
        # 原文逐字符换行 → 去空白得到连续文本（保留全角标点）
        stripped = re.sub(r"\s+", "", raw)
        subj = await conn.fetchrow("SELECT id FROM subjects WHERE name = '物理'")
        subject_id = str(subj["id"])

        # 管线选项（从任务结果复用，已确认与源一致）
        task = await conn.fetchrow(
            """
            SELECT result_json FROM background_tasks
            WHERE payload_json->>'document_id' = $1 ORDER BY created_at DESC LIMIT 1
            """,
            doc_id,
        )
        res = json.loads(task["result_json"] or "{}") if task else {}
        pipe_qs = {str(q.get("question_number")): q for q in res.get("questions", []) if isinstance(q, dict)}

        plans = [
            ("4", Q4_START, Q4_END, "A", pipe_qs.get("4", {}).get("options")),
            ("7", Q7_START, Q7_END, "B", pipe_qs.get("7", {}).get("options")),
        ]
        # L2 stem_start_marker 修正：mimo OCR 给自主命制题加了幻觉标题
        # （"4.滑沙项目受力与运动分析"），与 pdf_raw 题干不符，导致 e2e
        # 题干起始标记校验失败。改为真实题干开头。
        l2_corrections = {
            "4": Q4_START,
            "7": Q7_START,
        }
        for qn, start_m, end_m, answer, options in plans:
            # 幂等：该文档该题号已存在则跳过
            exists = await conn.fetchval(
                """
                SELECT 1 FROM question_instances qi
                JOIN questions q ON q.id = qi.question_id
                WHERE qi.document_id = $1 AND qi.source_question_number = $2
                """,
                doc_id,
                qn,
            )
            if exists:
                print(f"Q{qn}: 已存在，跳过")
                continue
            stem = extract_stem(stripped, start_m, end_m)
            if not stem:
                print(f"Q{qn}: 无法从 pdf_raw 提取题干（start={start_m[:20]!r}），跳过")
                continue
            options = options or []
            content_hash = compute_hash(stem, options)
            # 去重：content_hash 命中现有 Question 则只建 Instance
            existing_qid = await conn.fetchval(
                "SELECT id FROM questions WHERE content_hash = $1 AND subject_id = $2",
                content_hash,
                subject_id,
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
                    qid,
                    subject_id,
                    doc["grade"],
                    SINGLE_CHOICE_TYPE,
                    stem,
                    json.dumps(options, ensure_ascii=False),
                    answer,
                    doc["filename"],
                    content_hash,
                )
                print(f"Q{qn}: 新建 Question {qid} (stem {len(stem)} 字符)")
            inst_id = str(uuid.uuid4())
            await conn.execute(
                """
                INSERT INTO question_instances
                  (id, question_id, source_type, source_document_name, source_page,
                   source_question_number, year, school, occurrence_no, created_at, document_id)
                VALUES ($1, $2, 'document', $3, 9, $4, $5, $6, 1, now(), $7)
                """,
                inst_id,
                qid,
                doc["filename"],
                qn,
                doc["year"],
                doc["school"],
                doc_id,
            )
            # occurrence_count 维护
            await conn.execute(
                "UPDATE questions SET occurrence_count = (SELECT count(*) FROM question_instances WHERE question_id = $1) WHERE id = $1",
                qid,
            )
            print(f"Q{qn}: 已回填（question={str(qid)[:8]}…, instance={str(inst_id)[:8]}…, answer={answer}）")

        # L2 stem_start_marker 修正（幂等：仅当当前值为 OCR 幻觉标题时替换）
        l2_raw = doc_meta and doc_meta["llm_annotated_markdown"] or "{}"
        try:
            l2_data = json.loads(l2_raw)
        except Exception:
            l2_data = {}
        changed = False
        for q in l2_data.get("questions", []):
            qn = str(q.get("question_number"))
            if qn in l2_corrections:
                cur = q.get("stem_start_marker") or ""
                if cur and cur not in l2_corrections[qn] and l2_corrections[qn] not in cur:
                    q["stem_start_marker"] = l2_corrections[qn]
                    changed = True
                    print(f"L2 Q{qn}: stem_start_marker {cur[:20]!r} -> {l2_corrections[qn][:20]!r}")
        if changed:
            await conn.execute(
                "UPDATE documents SET llm_annotated_markdown = $1 WHERE id = $2",
                json.dumps(l2_data, ensure_ascii=False),
                doc_id,
            )
            print("L2 已更新")
    finally:
        await conn.close()


asyncio.run(main())

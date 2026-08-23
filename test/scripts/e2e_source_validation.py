#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""e2e 源数据对齐：原始 PDF、native_markdown、ocr_markdown、L2/管线、DB。

用途：
- 验证 e2e_semantic_report.py 的结论不是“DB 与已存产物自洽”，而是能与原始 PDF 对齐。
- 输出整体文本覆盖率，以及关键问题题目的 raw/native/ocr/pipeline/DB 证据。

运行：
    python test/scripts/e2e_source_validation.py
"""

from __future__ import annotations

import argparse
import asyncio
import io
import json
import os
import sys
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PDF_ROOT = PROJECT_ROOT / "test" / "pdf"
DSN = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:15432/aitutors",
)


def compact_text(text: str | None) -> str:
    if not text:
        return ""
    out: list[str] = []
    for ch in str(text):
        code = ord(ch)
        if ch in "\u2018\u2019":
            out.append("'")
            continue
        if ch in "\u201c\u201d":
            out.append('"')
            continue
        if ch == "\u3000":
            continue
        if 0xFF01 <= code <= 0xFF5E:
            out.append(chr(code - 0xFEE0))
            continue
        if ch.isspace():
            continue
        out.append(ch)
    return "".join(out)


def chunk_coverage(needle: str | None, haystack_compact: str, size: int = 40) -> float:
    compact_needle = compact_text(needle)
    if not compact_needle:
        return 1.0
    chunks = [
        compact_needle[i : i + size]
        for i in range(0, max(1, len(compact_needle)), size)
    ]
    if not chunks:
        return 1.0
    hits = sum(1 for chunk in chunks if chunk in haystack_compact)
    return hits / len(chunks)


def load_json(value) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def find_pdf(subject: str) -> Path | None:
    keywords: list[str] = []
    if subject == "\u82f1\u8bed":
        keywords = ["\u82f1\u8bed", "\u4e1c\u57ce"]
    elif subject == "\u8bed\u6587":
        keywords = ["\u8bed\u6587", "\u671d\u9633"]
    elif subject == "\u6570\u5b66":
        keywords = ["\u6570\u5b66"]
    elif subject == "\u7269\u7406":
        keywords = ["\u7269\u7406"]
    elif subject == "\u5316\u5b66":
        keywords = ["\u5316\u5b66"]
    elif subject == "\u751f\u7269":
        keywords = ["\u751f\u7269"]
    elif subject == "\u5730\u7406":
        keywords = ["\u5730\u7406"]
    elif subject == "\u5386\u53f2":
        keywords = ["\u5386\u53f2"]
    elif subject == "\u653f\u6cbb":
        keywords = ["\u653f\u6cbb"]
    if not keywords:
        return None
    for path in PDF_ROOT.glob("*.pdf"):
        if all(keyword in path.name for keyword in keywords):
            return path
    return None


def source_snippet(text: str, needle: str, width: int = 120) -> str:
    pos = text.find(needle)
    if pos < 0:
        return f"NOT_FOUND: {needle[:40]}"
    return text[max(0, pos - 40) : pos + width].replace("\n", "\\n")


async def main() -> None:
    parser = argparse.ArgumentParser(description="e2e 源数据对齐")
    parser.add_argument("--subject", type=str, default="", help="指定学科")
    parser.add_argument("--output", type=str, default="", help="报告输出路径")
    args = parser.parse_args()

    import asyncpg
    import fitz

    conn = await asyncpg.connect(DSN)
    try:
        if args.subject:
            docs = await conn.fetch(
                """
                SELECT id, subject, filename, native_markdown, ocr_markdown, llm_annotated_markdown
                FROM documents
                WHERE subject = $1 AND processing_status = 'completed'
                """,
                args.subject,
            )
        else:
            docs = await conn.fetch(
                """
                SELECT id, subject, filename, native_markdown, ocr_markdown, llm_annotated_markdown
                FROM documents
                WHERE processing_status = 'completed'
                ORDER BY subject
                """
            )

        tasks = await conn.fetch("SELECT result_json, payload_json FROM background_tasks")
        task_by_doc: dict[str, dict] = {}
        for task in tasks:
            payload = load_json(task["payload_json"])
            doc_id = str(payload.get("document_id") or "")
            if doc_id:
                task_by_doc[doc_id] = load_json(task["result_json"])

        db_rows = await conn.fetch(
            """
            SELECT d.subject, qi.source_question_number, q.stem, q.options, q.answer
            FROM questions q
            JOIN question_instances qi ON qi.question_id = q.id
            JOIN documents d ON d.id = qi.document_id
            WHERE d.processing_status = 'completed'
            ORDER BY d.subject, qi.source_question_number::int
            """
        )

        reports: list[str] = []
        for doc in docs:
            subject = str(doc["subject"])
            pdf_path = find_pdf(subject)
            if not pdf_path:
                reports.append(f"{subject}: PDF NOT FOUND")
                continue

            with fitz.open(pdf_path) as pdf_doc:
                raw_text = "\n".join(page.get_text("text") for page in pdf_doc)
                page_count = len(pdf_doc)

            native_text = str(doc["native_markdown"] or "")
            ocr_text = str(doc["ocr_markdown"] or "")
            l2_data = load_json(doc["llm_annotated_markdown"])
            l2_by_qn = {
                str(q.get("question_number")): q
                for q in (l2_data.get("questions") or [])
                if isinstance(q, dict)
            }
            raw_compact = compact_text(raw_text)
            native_compact = compact_text(native_text)
            ocr_compact = compact_text(ocr_text)

            lines = [
                f"===== {subject} 源数据对齐 =====",
                f"PDF: {pdf_path.name} ({page_count} pages, {len(raw_text)} chars)",
                f"native_markdown: {len(native_text)} chars",
                f"ocr_markdown: {len(ocr_text)} chars",
                f"覆盖 raw->native: {chunk_coverage(raw_text, native_compact):.3f}",
                f"覆盖 native->raw: {chunk_coverage(native_text, raw_compact):.3f}",
                f"覆盖 raw->ocr: {chunk_coverage(raw_text, ocr_compact):.3f}",
                f"覆盖 ocr->raw: {chunk_coverage(ocr_text, raw_compact):.3f}",
            ]

            task_result = task_by_doc.get(str(doc["id"]), {})
            pipeline_by_qn = {
                str(q.get("question_number")): q
                for q in (task_result.get("questions") or [])
                if isinstance(q, dict)
            }
            db_by_subject = {
                str(r["source_question_number"]): r
                for r in db_rows
                if r["subject"] == subject
            }

            probe_rows: list[tuple[str, str, str]] = []
            if subject == "\u8bed\u6587":
                probe_rows = [
                    ("1", "stem", "\u4e8c\u3001\u672c\u5927\u9898\u51716\u5c0f\u9898"),
                    ("17", "stem", "\u56db\u3001\u672c\u5927\u9898\u51714\u5c0f\u9898"),
                    ("17", "stem", "\u5230\u6cd7\u6d2a\u53bb"),
                ]
            elif subject == "\u82f1\u8bed":
                probe_rows = [
                    ("26", "stem", "Welcome to the Camp Association"),
                    ("37", "stem", "We live in a culture addicted to winning"),
                    ("37", "stem", "\u7b2c\u4e09\u90e8\u5206"),
                ]

            if probe_rows:
                lines.append("")
                lines.append("关键证据 raw / native / ocr / pipeline / DB：")
                for qn, field, probe in probe_rows:
                    db_row = db_by_subject.get(qn) or {}
                    pipeline_q = pipeline_by_qn.get(qn) or {}
                    l2_q = l2_by_qn.get(qn) or {}
                    if field == "stem":
                        db_text = str(db_row.get("stem") or "")
                        shared_text = str(pipeline_q.get("shared_material") or "")
                    else:
                        db_text = json.dumps(db_row.get(field), ensure_ascii=False)
                        shared_text = ""
                    c_probe = compact_text(probe)
                    llm_summary = (
                        f"composite={l2_q.get('is_composite')} "
                        f"shared_ids={len(l2_q.get('shared_material_line_ids') or [])} "
                        f"options_ids={len(l2_q.get('options_line_ids') or {})} "
                        f"subq={len(l2_q.get('sub_questions') or [])} "
                        f"start={str(l2_q.get('stem_start_marker') or '')[:40]!r}"
                    )
                    lines.append(
                        f"Q{qn} {field} {probe[:50]!r} "
                        f"raw={c_probe in raw_compact} "
                        f"native={c_probe in native_compact} "
                        f"ocr={c_probe in ocr_compact} "
                        f"pipeline_shared={c_probe in compact_text(shared_text)} "
                        f"db={c_probe in compact_text(db_text)}"
                    )
                    lines.append(f"  llm_md: {llm_summary}")
                    if c_probe in raw_compact:
                        lines.append(f"  raw snippet: {source_snippet(raw_compact, c_probe)}")

            reports.append("\n".join(lines))

        output = "\n\n".join(reports)
        print(output)
        if args.output:
            out_path = Path(args.output)
            if not out_path.is_absolute():
                out_path = PROJECT_ROOT / out_path
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(output, encoding="utf-8")
            print(f"\n报告已写入: {out_path}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""验证所有学科：DB 答案是否真实存在（不依赖 e2e 脚本的简单匹配）。"""
import asyncio
import json
import re
import sys
import io

if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"

def compact_text(text):
    if not text:
        return ""
    out = []
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

def extract_answer_section(text):
    if not text:
        return ""
    patterns = ["参考答案", "答案[：:]", r"Answer\s*Key", "【答案】"]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return text[m.start():]
    return ""

async def main():
    import asyncpg
    conn = await asyncpg.connect(DSN)
    try:
        rows = await conn.fetch(
            "SELECT id, filename, subject, native_markdown, ocr_markdown "
            "FROM documents WHERE processing_status='completed' ORDER BY subject"
        )

        print(f"{'学科':<8}{'DB答案':<10}{'源区答案':<10}{'验证脚本假阴性':<15}")
        print("-" * 50)

        for row in rows:
            subject = row["subject"]
            source = row["ocr_markdown"] or row["native_markdown"] or ""

            db_rows = await conn.fetch(
                """
                SELECT qi.source_question_number, q.answer, q.sub_questions
                FROM questions q
                JOIN question_instances qi ON qi.question_id = q.id
                WHERE qi.document_id = $1
                """,
                str(row["id"]),
            )

            answer_section = extract_answer_section(source)
            answer_compact = compact_text(answer_section)

            db_has_answer = 0
            source_has_answer = 0
            false_negative = 0
            total = len(db_rows)

            for r in db_rows:
                qn = r["source_question_number"]
                answer = r["answer"] or ""
                subs = r["sub_questions"]
                if isinstance(subs, str):
                    try:
                        subs = json.loads(subs)
                    except:
                        subs = []

                # Check DB answer
                has_db_answer = bool(answer)
                if not has_db_answer and subs:
                    sub_answers = [s.get("answer") for s in (subs or []) if isinstance(s, dict) and s.get("answer")]
                    has_db_answer = bool(sub_answers)

                if has_db_answer:
                    db_has_answer += 1

                # Check if answer is in source answer section
                exp = compact_text(answer)
                if exp and answer_compact:
                    # Check with qn prefix (e2e script method)
                    first_20 = exp[:20]
                    found_with_qn = False
                    for p in [f"{qn}.{exp}", f"{qn}.{first_20}", f"{qn}{exp}", f"{qn}{first_20}", f"{qn} {exp}", f"{qn} {first_20}"]:
                        if p in answer_compact:
                            found_with_qn = True
                            break

                    # Check without qn prefix (actual answer text)
                    found_without_qn = exp in answer_compact or first_20 in answer_compact

                    if found_with_qn:
                        source_has_answer += 1
                    elif found_without_qn:
                        source_has_answer += 1
                        false_negative += 1  # e2e script would miss this

            print(f"{subject:<8}{db_has_answer}/{total:<8}{source_has_answer}/{total:<8}{false_negative}")

    finally:
        await conn.close()

asyncio.run(main())

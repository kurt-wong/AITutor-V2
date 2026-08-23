#!/usr/bin/env python3
"""对比 DB 答案 vs e2e 脚本验证：找出假阴性的根因。"""
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
        # Check chemistry
        doc = await conn.fetchrow(
            "SELECT id, filename, native_markdown, ocr_markdown "
            "FROM documents WHERE subject='化学' AND processing_status='completed' "
            "ORDER BY created_at DESC LIMIT 1"
        )
        source = doc["ocr_markdown"] or doc["native_markdown"] or ""

        db_rows = await conn.fetch(
            """
            SELECT qi.source_question_number, q.answer, q.sub_questions, q.options
            FROM questions q
            JOIN question_instances qi ON qi.question_id = q.id
            WHERE qi.document_id = $1
            ORDER BY qi.source_question_number::int
            """,
            str(doc["id"]),
        )

        answer_section = extract_answer_section(source)
        answer_compact = compact_text(answer_section)
        print(f"Answer section length: {len(answer_section)} chars")
        print(f"Answer section compact length: {len(answer_compact)} chars")
        print(f"Answer section first 200 chars: {repr(answer_compact[:200])}")

        for r in db_rows[:5]:
            qn = r["source_question_number"]
            answer = r["answer"] or ""
            subs = r["sub_questions"]
            if isinstance(subs, str):
                try:
                    subs = json.loads(subs)
                except:
                    subs = []

            print(f"\nQ{qn}: DB answer={repr(answer[:80])}")

            # Check if answer is in answer_section
            exp = compact_text(answer)
            if exp:
                # Simple pattern matching (like e2e script)
                first_20 = exp[:20]
                patterns_to_try = [
                    f"{qn}.{exp}",
                    f"{qn}.{first_20}",
                    f"{qn}{exp}",
                    f"{qn}{first_20}",
                    f"{qn} {exp}",
                    f"{qn} {first_20}",
                ]
                found = False
                for p in patterns_to_try:
                    if p in answer_compact:
                        print(f"  FOUND via pattern: {repr(p[:60])}")
                        found = True
                        break
                if not found:
                    # Try finding answer without qn prefix
                    if exp in answer_compact:
                        print(f"  FOUND answer text (no qn prefix)")
                    elif first_20 in answer_compact:
                        print(f"  FOUND first 20 chars (no qn prefix)")
                    else:
                        print(f"  NOT FOUND in answer section")
                        # Show what's around the answer in the table
                        # Look for the answer in HTML table format
                        ans_in_source = compact_text(answer)
                        if ans_in_source in compact_text(source):
                            pos = compact_text(source).find(ans_in_source)
                            ctx = source[max(0,pos-50):pos+50] if pos >= 0 else "N/A"
                            print(f"  Answer found in full source @{pos}: {repr(ctx[:100])}")

    finally:
        await conn.close()

asyncio.run(main())

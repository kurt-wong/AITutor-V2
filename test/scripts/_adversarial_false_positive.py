#!/usr/bin/env python3
"""对抗性审查：检查 e2e 答案验证修复是否引入假阳性。

对每个学科，检查：
1. 修正前失败、修正后通过的题目，答案是否真实存在于答案区
2. 短答案（≤5字符）是否可能匹配到非答案文本（如选项标签）
"""
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

        total_checked = 0
        potential_false_positives = []

        for row in rows:
            subject = row["subject"]
            source = row["ocr_markdown"] or row["native_markdown"] or ""
            answer_section = extract_answer_section(source)
            answer_compact = compact_text(answer_section)

            if not answer_compact:
                print(f"{subject}: NO ANSWER SECTION - cannot verify")
                continue

            db_rows = await conn.fetch(
                """
                SELECT qi.source_question_number, q.answer, q.options
                FROM questions q
                JOIN question_instances qi ON qi.question_id = q.id
                WHERE qi.document_id = $1
                ORDER BY qi.source_question_number::int
                """,
                str(row["id"]),
            )

            for r in db_rows:
                qn = r["source_question_number"]
                answer = r["answer"] or ""
                exp = compact_text(answer)
                if not exp:
                    continue

                total_checked += 1

                # Check with qn prefix (old method)
                first_20 = exp[:20]
                found_with_qn = False
                for p in [f"{qn}.{exp}", f"{qn}.{first_20}", f"{qn}{exp}", f"{qn}{first_20}", f"{qn} {exp}", f"{qn} {first_20}"]:
                    if p in answer_compact:
                        found_with_qn = True
                        break

                # Check without qn prefix (new method)
                if len(exp) <= 5:
                    found_without_qn = exp in answer_compact
                else:
                    found_without_qn = first_20 in answer_compact

                if found_without_qn and not found_with_qn:
                    # This is a question that would pass with new method but not old
                    # Check if it's a potential false positive
                    is_short = len(exp) <= 5
                    if is_short:
                        # Count occurrences of the answer in answer section
                        count = answer_compact.count(exp)
                        # Check if answer appears in non-answer context
                        # (e.g., "B选项" vs just "B")
                        # For short answers, we need to be more careful
                        potential_false_positives.append({
                            "subject": subject,
                            "qn": qn,
                            "answer": exp,
                            "occurrences": count,
                            "is_single_char": len(exp) == 1,
                        })

        print(f"\nTotal questions checked: {total_checked}")
        print(f"Potential false positives (short answers without qn prefix): {len(potential_false_positives)}")

        if potential_false_positives:
            print("\nDetailed false positive analysis:")
            for fp in potential_false_positives:
                risk = "HIGH" if fp["is_single_char"] and fp["occurrences"] > 10 else "MEDIUM" if fp["is_single_char"] else "LOW"
                print(f"  {fp['subject']} Q{fp['qn']}: answer='{fp['answer']}' "
                      f"occurrences={fp['occurrences']} risk={risk}")

    finally:
        await conn.close()

asyncio.run(main())

#!/usr/bin/env python3
"""对抗性审查：检查 native_markdown 中答案区的实际格式。"""
import asyncio
import re
import sys
import io

if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"

async def main():
    import asyncpg
    conn = await asyncpg.connect(DSN)
    try:
        for subject in ["化学", "政治", "生物", "数学", "物理"]:
            doc = await conn.fetchrow(
                "SELECT id, filename, native_markdown "
                "FROM documents WHERE subject=$1 AND processing_status='completed' "
                "ORDER BY created_at DESC LIMIT 1",
                subject,
            )
            if not doc:
                continue

            native = doc["native_markdown"] or ""
            
            # Find answer section
            answer_match = re.search("参考答案", native)
            if not answer_match:
                print(f"{subject}: NO '参考答案' in native_markdown")
                continue
            
            answer_section = native[answer_match.start():]
            print(f"\n=== {subject} ===")
            print(f"Answer section ({len(answer_section)} chars):")
            
            # Show first 500 chars
            print(f"  First 500 chars:")
            for line in answer_section[:500].split('\n')[:15]:
                print(f"    {repr(line[:80])}")
            
            # Try to parse answers from native text
            # Look for patterns like "(1) A" or "1. A" or "1 A"
            answers = {}
            
            # Pattern 1: (题号) 答案
            for m in re.finditer(r"[（(]\s*(\d{1,3})\s*[）)]\s*([A-D]{1,4})", answer_section):
                qn = m.group(1)
                if qn not in answers:
                    answers[qn] = m.group(2)
            
            # Pattern 2: 题号. 答案
            for m in re.finditer(r"(?<!\d)(\d{1,3})\s*[.、．]\s*([A-D]{1,4})", answer_section):
                qn = m.group(1)
                if qn not in answers:
                    answers[qn] = m.group(2)
            
            # Pattern 3: 题号 答案 (with space)
            for m in re.finditer(r"(?<!\d)(\d{1,3})\s+([A-D]{1,4})(?!\w)", answer_section):
                qn = m.group(1)
                if qn not in answers:
                    answers[qn] = m.group(2)
            
            print(f"\n  Parsed answers: {len(answers)}")
            if answers:
                for qn in sorted(answers.keys(), key=lambda x: int(x))[:10]:
                    print(f"    Q{qn}: {answers[qn]}")

    finally:
        await conn.close()

asyncio.run(main())

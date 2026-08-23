#!/usr/bin/env python3
"""诊断答案区检测：检查各学科文档中答案区标记的实际位置。"""
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
        rows = await conn.fetch(
            "SELECT id, filename, subject, native_markdown, ocr_markdown "
            "FROM documents WHERE processing_status = 'completed' ORDER BY subject"
        )
        for row in rows:
            subject = row["subject"]
            source = row["ocr_markdown"] or row["native_markdown"] or ""
            print(f"\n=== {subject} ({row['filename']}) ===")
            print(f"  Source length: {len(source)} chars")

            # Check answer section markers
            patterns = {
                "参考答案": re.compile("参考答案"),
                "答案": re.compile("答案"),
                "Answer Key": re.compile(r"Answer\s*Key", re.IGNORECASE),
                "【答案】": re.compile("【答案】"),
            }
            for name, pat in patterns.items():
                matches = list(pat.finditer(source))
                if matches:
                    print(f"  '{name}': {len(matches)} matches")
                    for m in matches[:3]:
                        ctx = source[m.start():min(m.start()+80, len(source))]
                        print(f"    @{m.start()}: {repr(ctx)}")
                else:
                    print(f"  '{name}': NOT FOUND")

            # Check last 2000 chars for answer patterns
            tail = source[-2000:] if len(source) > 2000 else source
            answer_pat = re.compile(r"(?:参考答案|答案|Answer\s*Key)(?:\s*[:：]|$)", re.IGNORECASE)
            tail_matches = list(answer_pat.finditer(tail))
            if tail_matches:
                print(f"  Tail answer section: {len(tail_matches)} matches in last 2000 chars")
            else:
                print(f"  Tail answer section: NO matches in last 2000 chars")

    finally:
        await conn.close()

asyncio.run(main())

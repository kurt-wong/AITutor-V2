"""诊断：化学试卷 L1 原始文本，查看选项排布。"""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

import os
_backend_env = ROOT / "backend" / ".env"
if _backend_env.exists():
    for line in _backend_env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())

from app.domains.document.ocr.providers import build_ocr_chain
from app.domains.document.ppsv3_l1 import extract_l1_from_ocr


async def main():
    pdf = ROOT / "test" / "pdf" / "2026北京八一学校高一（上）期末化学（教师版）.pdf"
    if not pdf.exists():
        print(f"PDF not found: {pdf}")
        return

    chain = build_ocr_chain()
    print(f"OCR chain: {[p.name for p in chain.providers]}")

    print("Running OCR...")
    ocr_doc = await chain.extract(pdf)
    print(f"OCR provider: {ocr_doc.provider_used}, pages: {len(ocr_doc.pages)}")

    l1 = extract_l1_from_ocr(ocr_doc, filename=pdf.name)
    print(f"L1 lines: {len(l1.lines)}")

    # 找选项行（行文本含 (A)/(B)/A./B./（A）等模式）
    import re
    option_re = re.compile(r"^\s*[（(]?\s*([A-G])\s*[）)]?\s*[.、．]?\s*")

    lines = []
    for line in l1.lines:
        m = option_re.match(line.text)
        if m:
            lines.append(f"[{line.line_id}] {line.text[:120]}")

    out = []
    out.append(f"Total L1 lines: {len(l1.lines)}")
    out.append(f"Total option-like lines: {len(lines)}")
    out.append("")
    out.append("=== Option-like lines (first 80) ===")
    for l in lines[:80]:
        out.append(l)

    # 重点：Q11 附近的行（P2L015-P2L030 区域）
    out.append("")
    out.append("=== Lines around Q11 (P2L010-P2L030) ===")
    for line in l1.lines:
        if line.line_id.startswith("P2L") and 10 <= int(line.line_id[3:]) <= 35:
            out.append(f"[{line.line_id}] {line.text[:150]}")

    # Q16 附近的行（P3L001-P3L020）
    out.append("")
    out.append("=== Lines around Q16 (P3L001-P3L020) ===")
    for line in l1.lines:
        if line.line_id.startswith("P3L") and 1 <= int(line.line_id[3:]) <= 25:
            out.append(f"[{line.line_id}] {line.text[:150]}")

    # Q18 附近的行（P3L030-P4L010）
    out.append("")
    out.append("=== Lines around Q18 (P3L025-P4L010) ===")
    for line in l1.lines:
        if line.line_id.startswith("P3L") and 25 <= int(line.line_id[3:]) <= 40:
            out.append(f"[{line.line_id}] {line.text[:150]}")
        elif line.line_id.startswith("P4L") and 1 <= int(line.line_id[3:]) <= 10:
            out.append(f"[{line.line_id}] {line.text[:150]}")

    p = ROOT / "test" / "results" / "_diag_chem_l1.txt"
    p.write_text("\n".join(out), encoding="utf-8")
    print(f"Written to {p}")


asyncio.run(main())

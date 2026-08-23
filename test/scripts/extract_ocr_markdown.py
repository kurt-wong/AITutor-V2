#!/usr/bin/env python3
"""批量提取所有测试PDF的OCR markdown。

只跑OCR部分（PP-StructureV3 或 PaddleOCR-VL），不跑LLM标注。
输出每份PDF的markdown文本到 test/ocr_markdown/ 目录。

用法：
  python extract_ocr_markdown.py              # 全部PDF
  python extract_ocr_markdown.py --limit 5    # 前5份
  python extract_ocr_markdown.py --subject 英语  # 只跑英语

输出：
  test/ocr_markdown/{filename}.md             # 每份PDF的OCR markdown
  test/ocr_markdown/summary.json              # 汇总信息
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "test" / "scripts"))

# 加载 .env
_backend_env = ROOT / "backend" / ".env"
if _backend_env.exists():
    for line in _backend_env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

from app.domains.document.ocr.providers import build_ocr_chain
from app.domains.document.ppsv3_l1 import extract_l1_from_ocr
from app.domains.document.simple_pipeline import _ocr_model_for_subject, _extract_subject_from_filename

PDF_DIR = ROOT / "test" / "pdf"
OUTPUT_DIR = ROOT / "test" / "ocr_markdown"

# 学科OCR模型路由（与simple_pipeline一致）
_SUBJECT_OCR_MODEL = {
    "化学": "PaddleOCR-VL-1.6",
}
_DEFAULT_OCR_MODEL = "PP-StructureV3"


async def extract_one(pdf_path: Path, total_pdfs: int, idx: int) -> dict:
    """提取单份PDF的OCR markdown。"""
    filename = pdf_path.name
    stem = pdf_path.stem
    subject = _extract_subject_from_filename(filename)
    model = _ocr_model_for_subject(subject)

    print(
        f"[{time.strftime('%H:%M:%S')}] [{idx}/{total_pdfs}] {filename}",
        f"subject={subject} model={model}",
        flush=True,
    )
    started = time.perf_counter()

    try:
        # 1. 跑OCR
        ocr_chain = build_ocr_chain(model=model)
        try:
            ocr_doc = await ocr_chain.extract(pdf_path)
        finally:
            ocr_chain.close()

        # 2. 转成L1（保留结构信息）
        l1_doc = extract_l1_from_ocr(ocr_doc, filename=filename)

        # 3. 拼成纯文本markdown
        lines_text = [line.text for line in l1_doc.lines]
        markdown_text = "\n".join(lines_text)

        # 4. 保存
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        md_path = OUTPUT_DIR / f"{stem}.md"
        md_path.write_text(markdown_text, encoding="utf-8")

        # 5. 也保存带行号的版本（方便对照）
        lines_with_id = [
            f"{line.line_id} (P{line.page_no}L{line.line_no_in_page}): {line.text}"
            for line in l1_doc.lines
        ]
        numbered_path = OUTPUT_DIR / f"{stem}_numbered.md"
        numbered_path.write_text("\n".join(lines_with_id), encoding="utf-8")

        elapsed = round(time.perf_counter() - started, 1)
        print(
            f"  -> OK: {len(l1_doc.lines)} lines, {len(markdown_text)} chars, "
            f"{elapsed}s",
            flush=True,
        )

        return {
            "filename": filename,
            "subject": subject,
            "model": model,
            "status": "ok",
            "line_count": len(l1_doc.lines),
            "char_count": len(markdown_text),
            "page_count": l1_doc.total_pages,
            "elapsed_s": elapsed,
            "md_path": str(md_path),
            "numbered_path": str(numbered_path),
        }

    except Exception as exc:
        elapsed = round(time.perf_counter() - started, 1)
        print(f"  -> FAILED: {exc}", file=sys.stderr, flush=True)
        return {
            "filename": filename,
            "subject": subject,
            "model": model,
            "status": "failed",
            "error": str(exc),
            "elapsed_s": elapsed,
        }


async def main() -> int:
    parser = argparse.ArgumentParser(description="批量提取OCR markdown")
    parser.add_argument("--limit", type=int, default=None, help="最多处理份数")
    parser.add_argument("--subject", type=str, default=None, help="只处理指定学科")
    args = parser.parse_args()

    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    if args.subject:
        pdfs = [p for p in pdfs if args.subject in p.name]
    if args.limit:
        pdfs = pdfs[: args.limit]

    if not pdfs:
        print("No PDF files found.")
        return 1

    print(f"Processing {len(pdfs)} PDFs...", flush=True)

    summary = []
    for idx, pdf_path in enumerate(pdfs, 1):
        result = await extract_one(pdf_path, len(pdfs), idx)
        summary.append(result)

        # 每完成一份就更新summary
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        summary_path = OUTPUT_DIR / "summary.json"
        summary_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # 最终统计
    ok_count = sum(1 for r in summary if r["status"] == "ok")
    fail_count = sum(1 for r in summary if r["status"] == "failed")
    print(f"\nDone: {ok_count} ok, {fail_count} failed out of {len(summary)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

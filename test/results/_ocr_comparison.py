"""OCR 对照测试：PP-StructureV3 vs PaddleOCR-VL。

5 科各 1 份 PDF，分别用两种模型跑 L1，输出对比报告。
"""
import asyncio
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

_backend_env = ROOT / "backend" / ".env"
if _backend_env.exists():
    for line in _backend_env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())

from app.domains.document.ocr.paddle_client import PaddleOCRClient
from app.domains.document.ppsv3_l1 import extract_l1_from_ocr
from app.domains.document.ocr_l1_converter import convert_ocr_to_l1
from app.core.config import settings

PDF_DIR = ROOT / "test" / "pdf"
OUTPUT_DIR = ROOT / "test" / "results" / "ocr_comparison"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 5 科代表 PDF
TARGETS = [
    ("化学", "2026北京八一学校高一（上）期末化学（教师版）.pdf"),
    ("生物", "2026北京北师大附中高一（上）期末生物（教师版）.pdf"),
    ("地理", "2026北京朝阳高一（上）期末地理（教师版）.pdf"),
    ("语文", "2026北京八十中高一（上）期末语文（教师版）.pdf"),
    ("数学", "2026北京二中高一（上）期末数学（教师版）.pdf"),
]

MODELS = ["PP-StructureV3", "PaddleOCR-VL"]

import re

_OPTION_LABEL_RE = re.compile(r"^\s*[（(]?\s*([A-G])\s*[）)]?\s*[.、．]?\s*")
_QUESTION_NUM_RE = re.compile(r"^\s*(\d{1,3})\s*[.、．]")
_TABLE_TAG_RE = re.compile(r"<table|<tr|<td")
_LATEX_RE = re.compile(r"\$[^$]+\$|\\[a-zA-Z]+")


def _analyze_l1(l1, subject: str) -> dict:
    """分析 L1 文档质量指标。"""
    lines = l1.lines
    total = len(lines)

    # 题号检测
    q_lines = [l for l in lines if _QUESTION_NUM_RE.match(l.text)]
    q_numbers = set()
    for l in lines:
        m = _QUESTION_NUM_RE.match(l.text)
        if m:
            q_numbers.add(int(m.group(1)))

    # 选项行检测
    option_lines = [l for l in lines if _OPTION_LABEL_RE.match(l.text)]
    option_labels = set()
    for l in option_lines:
        m = _OPTION_LABEL_RE.match(l.text)
        if m:
            option_labels.add(m.group(1))

    # 表格检测
    table_lines = [l for l in lines if _TABLE_TAG_RE.search(l.text)]

    # LaTeX/公式检测
    latex_lines = [l for l in lines if _LATEX_RE.search(l.text)]

    # 空行检测
    empty_lines = [l for l in lines if not (l.text or "").strip()]

    # 图片
    images = len(l1.images) if hasattr(l1, "images") and l1.images else 0

    return {
        "subject": subject,
        "total_lines": total,
        "question_count": len(q_numbers),
        "question_numbers": sorted(q_numbers),
        "option_line_count": len(option_lines),
        "option_labels": sorted(option_labels),
        "table_line_count": len(table_lines),
        "latex_line_count": len(latex_lines),
        "empty_line_count": len(empty_lines),
        "image_count": images,
    }


async def run_one(client: PaddleOCRClient, pdf_path: Path, model: str) -> dict:
    """用指定模型跑一份 PDF 的 OCR + L1 转换。"""
    print(f"  [{model}] {pdf_path.name} ...", flush=True)
    started = time.perf_counter()
    try:
        ocr_doc = await client.extract(pdf_path, model=model)
        elapsed = round(time.perf_counter() - started, 1)
        l1 = convert_ocr_to_l1(ocr_doc, filename=pdf_path.name)
        analysis = _analyze_l1(l1, "")
        analysis["elapsed_s"] = elapsed
        analysis["status"] = "ok"
        analysis["provider"] = ocr_doc.provider_used
        print(
            f"  [{model}] OK lines={analysis['total_lines']} "
            f"questions={analysis['question_count']} "
            f"options={analysis['option_line_count']} "
            f"tables={analysis['table_line_count']} "
            f"latex={analysis['latex_line_count']} "
            f"elapsed={elapsed}s",
            flush=True,
        )
        # 保存 L1 原始行（用于人工检查）
        stem = pdf_path.stem
        l1_path = OUTPUT_DIR / f"{stem}_{model}_l1.json"
        l1_data = [
            {"line_id": l.line_id, "page": l.page_no, "text": l.text[:200]}
            for l in l1.lines
        ]
        l1_path.write_text(
            json.dumps(l1_data, ensure_ascii=False, indent=1),
            encoding="utf-8",
        )
        return analysis
    except Exception as exc:
        elapsed = round(time.perf_counter() - started, 1)
        print(f"  [{model}] FAILED ({elapsed}s): {exc}", flush=True)
        return {
            "status": "failed",
            "error": str(exc),
            "elapsed_s": elapsed,
        }


async def main():
    client = PaddleOCRClient(
        base_url=settings.paddleocr_api_base_url,
        token=settings.paddleocr_vl_token,
        timeout_seconds=settings.llm_request_timeout_seconds,
        poll_interval_seconds=settings.paddleocr_poll_interval_seconds,
        job_timeout_seconds=settings.paddleocr_job_timeout_seconds,
    )

    report = []
    for subject, filename in TARGETS:
        pdf_path = PDF_DIR / filename
        if not pdf_path.exists():
            print(f"SKIP {filename} (not found)", flush=True)
            continue

        print(f"\n{'='*60}", flush=True)
        print(f"{subject}: {filename}", flush=True)
        print(f"{'='*60}", flush=True)

        entry = {"subject": subject, "filename": filename, "results": {}}
        for model in MODELS:
            result = await run_one(client, pdf_path, model)
            result["subject"] = subject
            entry["results"][model] = result
        report.append(entry)

        # 逐科写入（避免全部跑完才保存）
        report_path = OUTPUT_DIR / "comparison_report.json"
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # 打印对比摘要
    print("\n" + "=" * 80, flush=True)
    print("OCR 对照测试摘要", flush=True)
    print("=" * 80, flush=True)
    print(
        f"{'科目':<6} {'指标':<16} {'PP-StructureV3':>16} {'PaddleOCR-VL':>16} {'差异':>10}",
        flush=True,
    )
    print("-" * 80, flush=True)
    for entry in report:
        pps = entry["results"].get("PP-StructureV3", {})
        vl = entry["results"].get("PaddleOCR-VL", {})
        if pps.get("status") != "ok" or vl.get("status") != "ok":
            print(f"{entry['subject']:<6} STATUS: PPS={pps.get('status')} VL={vl.get('status')}", flush=True)
            continue
        for key, label in [
            ("total_lines", "总行数"),
            ("question_count", "题号数"),
            ("option_line_count", "选项行数"),
            ("table_line_count", "表格行数"),
            ("latex_line_count", "公式行数"),
            ("empty_line_count", "空行数"),
            ("image_count", "图片数"),
            ("elapsed_s", "耗时(s)"),
        ]:
            pval = pps.get(key, 0)
            vval = vl.get(key, 0)
            diff = vval - pval if isinstance(pval, (int, float)) else ""
            print(
                f"{entry['subject']:<6} {label:<16} {pval:>16} {vval:>16} {diff:>+10}",
                flush=True,
            )
        print("-" * 80, flush=True)

    print(f"\n报告: {OUTPUT_DIR / 'comparison_report.json'}", flush=True)
    print(f"L1 原始数据: {OUTPUT_DIR}/*_l1.json", flush=True)


if __name__ == "__main__":
    asyncio.run(main())

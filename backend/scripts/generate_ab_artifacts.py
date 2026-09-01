"""生成 A/B 对比所需的 artifacts：L1 快照 + modular raw L2。

运行一次 pipeline，保存：
    1. L1 快照（带 P 行号）
    2. Modular raw L2（LLM 原始输出，不带人工修复）

每次运行自动带时间戳，不覆盖历史 artifact。

用法：
    python scripts/generate_ab_artifacts.py
    python scripts/generate_ab_artifacts.py --tag v3
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv
load_dotenv()

from app.ai.gateway import LLMGateway
from app.ai.providers.http import HTTPLLMProvider
from app.core.config import settings


def build_gateway() -> LLMGateway:
    provider = HTTPLLMProvider(
        name="deepseek",
        base_url=settings.deepseek_base_url,
        api_key=settings.deepseek_api_key,
        model=settings.deepseek_model,
        timeout_seconds=float(settings.llm_request_timeout_seconds or 300),
    )
    return LLMGateway(mode="live", providers=[provider])


async def run(tag: str | None = None):
    from app.domains.document.simple_pipeline import run_simple_pipeline

    pdf_path = BACKEND.parent / "test" / "pdf" / "2026北京东城高一（上）期末英语（教师版）.pdf"
    if not pdf_path.exists():
        print(f"PDF not found: {pdf_path}")
        return

    reports_dir = BACKEND / "reports"
    reports_dir.mkdir(exist_ok=True)

    l1_snapshot_path = reports_dir / "l1_snapshot_dongcheng_english.json"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = f"_{tag}" if tag else ""
    l2_output_path = reports_dir / f"l2_modular_{timestamp}{suffix}.json"
    l2_latest_path = reports_dir / "l2_modular_latest.json"

    gateway = build_gateway()
    print(f"Running pipeline: {pdf_path.name}")
    print(f"  L1 snapshot: {l1_snapshot_path}")
    print(f"  L2 output: {l2_output_path}")

    result = await run_simple_pipeline(
        pdf_path=pdf_path,
        subject="英语",
        gateway=gateway,
        use_modular_prompt=True,
        l1_snapshot_path=l1_snapshot_path,
    )

    print(f"\nPipeline result: {result.status}")
    print(f"  L1 lines: {len(result.l1_document.lines) if result.l1_document else 0}")

    if result.l2_annotation:
        from app.worker.document_worker import _serialize_l2_for_persistence
        l2_data = _serialize_l2_for_persistence(result.l2_annotation)
        l2_output_path.write_text(
            json.dumps(l2_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        l2_latest_path.write_text(
            json.dumps(l2_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"  L2 questions: {len(l2_data.get('questions', []))}")
        print(f"  L2 version: {l2_data.get('annotation_version')}")
        print(f"  Saved to: {l2_output_path}")
        print(f"  Latest: {l2_latest_path}")
    else:
        print("  ERROR: No L2 annotation produced")

    for stage in result.stages:
        print(f"  Stage {stage.get('name', '?')}: {stage.get('duration_ms', '?')}ms")

    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", help="Optional tag for L2 filename")
    args = parser.parse_args()
    result = asyncio.run(run(tag=args.tag))

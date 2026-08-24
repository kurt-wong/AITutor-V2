#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量恢复：重跑 ocr_unavailable 失败任务（OCR_PROVIDER_POLICY.md §5-3）。

流程：
1. 探测 paddle 可用性（提交小文件，HTTP < 400 即可用）。
2. 查询 background_tasks 中 status='failed' 且 error_detail 含
   'ocr_unavailable' 的任务。
3. paddle 可用 → 逐个调 retry API（POST /api/tasks/{id}/retry）。
4. paddle 不可用 → 打印提示，不重跑（等 paddle 恢复后再执行本脚本）。

用法：
    python backend/scripts/retry_ocr_unavailable.py [--dry-run]
"""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / "backend" / ".env")

API_BASE = "http://127.0.0.1:8000"
PADDLE_URL = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
PROBE_FILE = Path(__file__).resolve().parents[2] / "test" / "pdf" / "2026北京东城高一（上）期末英语（教师版）.pdf"


async def paddle_available() -> bool:
    """探测 paddle：提交小文件，HTTP < 400 即认为可用。"""
    token = os.environ.get("PADDLEOCR_VL_TOKEN", "")
    if not token:
        print("PADDLEOCR_VL_TOKEN 未配置，paddle 不可用")
        return False
    headers = {"Authorization": f"bearer {token}"}
    data = {
        "model": "PP-StructureV3",
        "optionalPayload": json.dumps({
            "useDocOrientationClassify": False,
            "useDocUnwarping": False,
            "useChartRecognition": False,
        }),
    }
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            with PROBE_FILE.open("rb") as f:
                resp = await client.post(
                    PADDLE_URL, headers=headers, data=data,
                    files={"file": (PROBE_FILE.name, f, "application/pdf")},
                )
        ok = resp.status_code < 400
        print(f"paddle 探测: HTTP {resp.status_code}"
              + ("" if ok else f" {resp.text[:120]}"))
        return ok
    except Exception as exc:
        print(f"paddle 探测失败: {exc}")
        return False


async def list_ocr_unavailable(client: httpx.AsyncClient) -> list[str]:
    """查询 ocr_unavailable 失败任务。"""
    tasks: list[str] = []
    page = 1
    while True:
        r = await client.get(
            f"{API_BASE}/api/tasks",
            params={"task_type": "document_parse", "status": "failed", "page": page, "page_size": 50},
        )
        data = r.json().get("data", {})
        items = data.get("items") or []
        for item in items:
            detail = str(item.get("error_detail") or "")
            if "ocr_unavailable" in detail:
                tasks.append(item["id"])
        if len(items) < 50:
            break
        page += 1
    return tasks


async def main(dry_run: bool) -> None:
    if not await paddle_available():
        print("paddle 不可用：不执行重跑，等 paddle 恢复后再运行本脚本")
        return
    async with httpx.AsyncClient(timeout=30) as client:
        failed = await list_ocr_unavailable(client)
        print(f"ocr_unavailable 失败任务: {len(failed)}")
        for tid in failed:
            print(f"  {tid}")
        if dry_run or not failed:
            return
        for tid in failed:
            r = await client.post(f"{API_BASE}/api/tasks/{tid}/retry")
            print(f"  retry {tid[:8]}: HTTP {r.status_code} {r.text[:100]}")
    print("批量恢复完成（任务已重新排队，worker 将按序处理）")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="只列出，不重跑")
    args = parser.parse_args()
    asyncio.run(main(args.dry_run))

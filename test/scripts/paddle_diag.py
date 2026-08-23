"""PaddleOCR API 诊断脚本 - 排查队列满问题"""
import json
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / "backend" / ".env")

# 从 backend/.env 或环境变量读取，禁止硬编码
TOKEN = os.environ.get("PADDLEOCR_VL_TOKEN", "")
if not TOKEN:
    raise SystemExit("PADDLEOCR_VL_TOKEN not found in backend/.env")
JOB_URL = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"

headers = {"Authorization": f"bearer {TOKEN}"}
optional_payload = {
    "useDocOrientationClassify": False,
    "useDocUnwarping": False,
    "useChartRecognition": False,
}

# 测试文件 - 用项目中最小的 PDF
TEST_PDF = Path(__file__).parent.parent / "pdf" / "2026北京东城高一（上）期末英语（教师版）.pdf"


def test_submit(model: str, file_path: Path | None = None, file_url: str | None = None) -> dict:
    """提交任务并返回完整响应"""
    print(f"\n{'='*60}")
    print(f"测试模型: {model}")
    print(f"提交方式: {'URL' if file_url else '文件'}")

    if file_url:
        h = {**headers, "Content-Type": "application/json"}
        payload = {
            "fileUrl": file_url,
            "model": model,
            "optionalPayload": optional_payload,
        }
        resp = requests.post(JOB_URL, json=payload, headers=h)
    else:
        data = {
            "model": model,
            "optionalPayload": json.dumps(optional_payload),
        }
        with open(file_path, "rb") as f:
            files = {"file": f}
            resp = requests.post(JOB_URL, headers=headers, data=data, files=files)

    print(f"HTTP Status: {resp.status_code}")
    try:
        body = resp.json()
        print(f"Response: {json.dumps(body, ensure_ascii=False, indent=2)}")
    except Exception:
        print(f"Response Text: {resp.text[:500]}")

    return {"status": resp.status_code, "body": resp.text}


def test_polling(job_id: str, model: str, max_polls: int = 6):
    """轮询任务状态"""
    print(f"\n--- 轮询任务 {job_id} (模型: {model}) ---")
    for i in range(max_polls):
        time.sleep(3)
        resp = requests.get(f"{JOB_URL}/{job_id}", headers=headers)
        if resp.status_code != 200:
            print(f"  Poll failed: {resp.status_code}")
            continue

        data = resp.json().get("data", {})
        state = data.get("state", "unknown")
        progress = data.get("extractProgress", {})
        print(f"  [{i+1}/{max_polls}] state={state}, "
              f"pages={progress.get('extractedPages', '?')}/{progress.get('totalPages', '?')}")

        if state in ("done", "failed"):
            return state, data
    return "timeout", {}


def main():
    print("=" * 60)
    print("PaddleOCR API 诊断")
    print("=" * 60)

    # 检查测试文件
    if TEST_PDF.exists():
        size_mb = TEST_PDF.stat().st_size / 1024 / 1024
        print(f"测试文件: {TEST_PDF.name} ({size_mb:.1f} MB)")
    else:
        print(f"测试文件不存在: {TEST_PDF}")
        sys.exit(1)

    results = {}

    # 测试1: PP-StructureV3 文件模式
    r1 = test_submit("PP-StructureV3", file_path=TEST_PDF)
    results["ppsv3_file"] = r1

    # 测试2: PaddleOCR-VL-1.6 文件模式 (如果 PP-StructureV3 失败)
    if r1["status"] != 200:
        r2 = test_submit("PaddleOCR-VL-1.6", file_path=TEST_PDF)
        results["paddle_vl_file"] = r2

    # 汇总
    print("\n" + "=" * 60)
    print("诊断汇总")
    print("=" * 60)
    for name, r in results.items():
        status = "✓ OK" if r["status"] == 200 else f"✗ FAIL ({r['status']})"
        print(f"  {name}: {status}")

    print("\n可能原因: 并发限制 / 速率限制 / 文件大小限制 / 模型独立配额")
    print("建议: 等待几分钟后重试，或尝试 PaddleOCR-VL-1.6 模型")


if __name__ == "__main__":
    main()

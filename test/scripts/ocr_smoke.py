#!/usr/bin/env python3
"""OCR smoke — 对 PP-StructureV3 / MIMO / DeepSeek Vision 各执行一次小文件验证。

输出 test/results/ocr_smoke.json：
  {
    "timestamp": ...,
    "file": "...",
    "providers": {
      "paddleocr": {"status": "ok" | "failed",
                    "provider": ..., "http_status": ..., "raw_body": ...,
                    "error": ..., "pages": N,
                    "provider_used": ..., "source_provider": ...},
      ...
    },
    "overall": "PASS" | "FAIL"
  }

用法:
  python ocr_smoke.py --provider all        # 全部 provider（默认）
  python ocr_smoke.py --provider paddleocr # 只跑指定 provider
  python ocr_smoke.py --file path.pdf      # 指定小文件（默认 test/pdf 中最小的 PDF）
"""

import argparse
import asyncio
import json
import logging
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
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

from app.core.config import settings
from app.domains.document.ocr.paddle_client import PaddleOCRClient, PaddleOCRClientError
from app.domains.document.ocr.providers import LLMVisionOCRProvider
from app.ai.gateway import LLMGateway
from app.ai.providers import HTTPLLMProvider

OUTPUT_PATH = ROOT / "test" / "results" / "ocr_smoke.json"

logger = logging.getLogger(__name__)


def extract_http_info(exc: Exception) -> dict:
    """从异常中提取可审计的 HTTP 信息（status / body）。

    支持 httpx.HTTPStatusError（response 属性）与 PaddleOCRClientError（消息内嵌）。
    body 的提取优先级：response.text > "HTTP xxx: <body>" > "raw=<片段>"。
    """
    status = None
    body = None
    response = getattr(exc, "response", None)
    if response is not None:
        status = getattr(response, "status_code", None)
        try:
            body = getattr(response, "text", None)
        except Exception:
            body = None
    if status is None:
        import re
        m = re.search(r"HTTP (\d{3})", str(exc))
        if m:
            status = int(m.group(1))
    if body is None:
        # 从 PaddleOCRClientError 消息中提取 "HTTP xxx: <body>"
        msg = str(exc)
        if "HTTP " in msg and ": " in msg:
            body = msg.split(": ", 1)[1]
        elif "raw=" in msg:
            # 格式类错误（HTTP 200 但内容不符合契约）：提取原始片段
            m = re.search(r"raw=('[^']*'|\"[^\"]*\")", msg)
            if m:
                body = m.group(1)
    if body is not None and len(str(body)) > 500:
        body = str(body)[:500]
    return {"http_status": status, "raw_body": body}


def summarize_failure(provider: str, exc: Exception) -> dict:
    """把 provider 失败转成 smoke 记录（status=failed）。"""
    info = extract_http_info(exc)
    return {
        "status": "failed",
        "provider": provider,
        "http_status": info["http_status"],
        "raw_body": info["raw_body"],
        "error": str(exc)[:500],
        "pages": None,
        "provider_used": None,
        "source_provider": None,
    }


def summarize_success(provider: str, document) -> dict:
    """把 provider 成功结果转成 smoke 记录（status=ok）。"""
    pages = len(document.pages) if document.pages else 0
    source_providers = sorted({p.source_provider for p in document.pages if p.source_provider})
    return {
        "status": "ok",
        "provider": provider,
        "http_status": None,
        "raw_body": None,
        "error": None,
        "pages": pages,
        "provider_used": getattr(document, "provider_used", None),
        "source_provider": source_providers,
    }


def validate_smoke_record(record: dict) -> list[str]:
    """校验单条 smoke 记录：成功必须有 pages，失败必须有明确 error。

    返回错误列表；空列表表示记录合法。
    """
    errors: list[str] = []
    if record.get("status") == "ok":
        if record.get("pages") is None or record.get("pages") < 1:
            errors.append("ok record missing pages")
        if not record.get("provider_used"):
            errors.append("ok record missing provider_used")
        if not record.get("source_provider"):
            errors.append("ok record missing source_provider")
    elif record.get("status") == "failed":
        if not record.get("error"):
            errors.append("failed record missing error")
        if record.get("http_status") is None and not record.get("raw_body"):
            errors.append("failed record missing http_status and raw_body")
    else:
        errors.append(f"unknown status: {record.get('status')!r}")
    return errors


def build_paddle_client() -> PaddleOCRClient:
    if not settings.paddleocr_vl_token:
        raise ValueError("PADDLEOCR_VL_TOKEN is not configured")
    return PaddleOCRClient(
        base_url=settings.paddleocr_api_base_url,
        token=settings.paddleocr_vl_token,
        timeout_seconds=settings.llm_request_timeout_seconds,
        poll_interval_seconds=settings.paddleocr_poll_interval_seconds,
        job_timeout_seconds=settings.paddleocr_job_timeout_seconds,
    )


def build_vision_provider(name: str) -> LLMVisionOCRProvider:
    if name == "mimo":
        mimo_model = settings.mimo_vl_model or settings.mimo_model
        if not (settings.mimo_api_key and settings.mimo_base_url and mimo_model):
            raise ValueError("MIMO 配置缺失")
        provider = HTTPLLMProvider(
            name="mimo-vl", base_url=settings.mimo_base_url,
            api_key=settings.mimo_api_key, model=mimo_model,
            timeout_seconds=settings.llm_request_timeout_seconds,
        )
    elif name == "deepseek_vl":
        if not (settings.deepseek_api_key and settings.deepseek_base_url and settings.deepseek_vl_model):
            raise ValueError("DEEPSEEK_VL 配置缺失")
        provider = HTTPLLMProvider(
            name="deepseek-vl", base_url=settings.deepseek_base_url,
            api_key=settings.deepseek_api_key, model=settings.deepseek_vl_model,
            timeout_seconds=settings.llm_request_timeout_seconds,
        )
    else:
        raise ValueError(f"unknown vision provider: {name}")
    return LLMVisionOCRProvider(
        name=name,
        gateway=LLMGateway(mode="live", providers=[provider]),
    )


def pick_smoke_file() -> Path:
    """选择 test/pdf 中最小的 PDF 作为 smoke 文件。"""
    pdfs = list((ROOT / "test" / "pdf").glob("*.pdf"))
    if not pdfs:
        raise FileNotFoundError("test/pdf 下没有 PDF")
    return min(pdfs, key=lambda p: p.stat().st_size)


async def run_provider(name: str, file_path: Path) -> dict:
    """执行单个 provider 的 smoke，返回记录。"""
    print(f"  [{name}] running on {file_path.name} ...")
    t0 = time.perf_counter()
    try:
        if name == "paddleocr":
            client = build_paddle_client()
            document = await client.extract(file_path)
        elif name in ("mimo", "deepseek_vl"):
            provider = build_vision_provider(name)
            document = await provider.extract(file_path)
        else:
            return {"status": "failed", "provider": name, "error": f"unknown provider: {name}"}
        record = summarize_success(name, document)
        elapsed = time.perf_counter() - t0
        print(f"  [OK]   {name}: pages={record['pages']} provider_used={record['provider_used']} "
              f"({elapsed:.1f}s)")
    except Exception as exc:
        record = summarize_failure(name, exc)
        elapsed = time.perf_counter() - t0
        print(f"  [FAIL] {name}: http_status={record['http_status']} error={str(exc)[:120]} "
              f"({elapsed:.1f}s)")
    record["elapsed_s"] = round(time.perf_counter() - t0, 1)
    return record


async def main() -> int:
    parser = argparse.ArgumentParser(description="OCR smoke 验证")
    parser.add_argument("--provider", choices=["all", "paddleocr", "mimo", "deepseek_vl"],
                        default="all")
    parser.add_argument("--file", type=str, default=None, help="smoke 文件（默认最小 PDF）")
    args = parser.parse_args()

    file_path = Path(args.file) if args.file else pick_smoke_file()
    print(f"OCR Smoke — file: {file_path.name}")

    if args.provider == "all":
        names = ["paddleocr", "mimo", "deepseek_vl"]
    else:
        names = [args.provider]

    providers: dict[str, dict] = {}
    for name in names:
        providers[name] = await run_provider(name, file_path)

    # 汇总校验
    errors: list[str] = []
    for name, record in providers.items():
        for e in validate_smoke_record(record):
            errors.append(f"{name}: {e}")

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "file": file_path.name,
        "providers": providers,
        "overall": "PASS" if not errors else "FAIL",
        "failures": errors,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nOCR Smoke {'PASS' if not errors else 'FAIL'}")
    for e in errors:
        print(f"  [FAIL] {e}")
    print(f"Report saved to: {OUTPUT_PATH}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

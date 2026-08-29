#!/usr/bin/env python3
"""校验 backend/.env 的 API key：存在性 + 是否仍是 git 历史泄露值（T0-2 安全）。

用法：
    python test/scripts/_verify_env_keys.py

输出（不打印完整密钥，只打状态与前缀）：
    PADDLEOCR_VL_TOKEN : OK (已轮换) / STILL LEAKED (仍为 dacad48 泄露值) / MISSING

泄露值来源：commit dacad48（诊断脚本硬编码），92a8c07 已从工作树移除但
密钥仍留在 git 历史，必须轮换后更新 backend/.env。
"""
import sys
import io
from pathlib import Path

from dotenv import load_dotenv

if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

load_dotenv(Path(__file__).resolve().parents[2] / "backend" / ".env")

# 泄露值（dacad48 引入，仅用于比对是否已轮换；不要在输出中打印完整值）
LEAKED = {
    "PADDLEOCR_VL_TOKEN": "5e6b7c1269811b4177fb6a7770a2ccfddb1029cc",
    "MIMO_API_KEY": "sk-cnolie3bj6swyssiji0dpuehvuop18csfqfph5a36hrxvpm0",
    "DEEPSEEK_API_KEY": "sk-96521bea50fb4eac88288e11e4415402",
}

print("=== API key 轮换状态检查 ===")
all_rotated = True
for key, leaked in LEAKED.items():
    import os
    value = os.environ.get(key, "")
    if not value:
        status = "MISSING"
        all_rotated = False
    elif value == leaked:
        status = "STILL LEAKED（未轮换，需在平台控制台重置）"
        all_rotated = False
    else:
        status = "OK（已轮换）"
    prefix = value[:8] + "..." if value else "-"
    print(f"  {key:<22}: {status}  [{prefix}]")

print()
if all_rotated:
    print("✅ 三个 key 均已轮换（或非泄露值），安全。")
else:
    print("⚠️  存在未轮换/缺失的 key。轮换步骤：")
    print("    1. 在各平台控制台重置对应 key：")
    print("       - PaddleOCR AIStudio（PADDLEOCR_VL_TOKEN）")
    print("       - MIMO 开放平台（MIMO_API_KEY）")
    print("       - DeepSeek 开放平台（DEEPSEEK_API_KEY）")
    print("    2. 将新 key 写入 backend/.env（.gitignore 中，不会入库）")
    print("    3. 重启后端后重跑本脚本，直到三个 key 均为 OK")
    print("    4. 历史泄露仍存在于 git 历史（dacad48），可考虑重写历史或接受风险")

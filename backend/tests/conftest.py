"""Pin test temp roots so sandbox temp ACLs cannot break pytest."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

# 2026-08-22 两次调整说明：
# 1. 最初固定到工作区 tmp/pytest：Codex 修复后曾可用，但沙箱会话变化后
#    该目录残留异常 ACL（读/写/删均 PermissionError），tmp_path 无法写文件。
# 2. 改 tmp/pytest_run 仍被锁（pytest 清理阶段创建后沙箱加锁）。
# 结论：工作区 tmp 下固定 basetemp 在沙箱中不稳定；改回系统 temp 下的
#   专属子目录（系统 temp 始终可写，专属名避免 dsh-* 随机目录问题）。
WORKSPACE_TMP = Path(tempfile.gettempdir()) / "aitutor_pytest"


def pytest_configure(config) -> None:
    WORKSPACE_TMP.mkdir(parents=True, exist_ok=True)
    config.option.basetemp = str(WORKSPACE_TMP)
    tempfile.tempdir = str(WORKSPACE_TMP)
    os.environ["TMPDIR"] = str(WORKSPACE_TMP)
    os.environ["TEMP"] = str(WORKSPACE_TMP)
    os.environ["TMP"] = str(WORKSPACE_TMP)

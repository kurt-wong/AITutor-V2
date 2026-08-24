"""Pin test temp roots + route pytest to the dedicated test database."""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

# 2026-08-22 两次调整说明：
# 1. 最初固定到工作区 tmp/pytest：Codex 修复后曾可用，但沙箱会话变化后
#    该目录残留异常 ACL（读/写/删均 PermissionError），tmp_path 无法写文件。
# 2. 改 tmp/pytest_run 仍被锁（pytest 清理阶段创建后沙箱加锁）。
# 结论：工作区 tmp 下固定 basetemp 在沙箱中不稳定；改回系统 temp 下的
#   专属子目录（系统 temp 始终可写，专属名避免 dsh-* 随机目录问题）。
WORKSPACE_TMP = Path(tempfile.gettempdir()) / "aitutor_pytest"

# 专用测试库（2026-08-25，v6.18）：同一 PostgreSQL 实例上的 <prod_db>_test
# （aitutors → aitutors_test）。背景：
# - phase2b 统计/搜索类测试断言"全表只有测试自身数据"（total==3 等），真实库
#   200+ 基线题会污染断言 → 需要空 questions 表的干净库；
# - 知识映射类测试依赖知识树（MATH-ANA-03 三角函数等）→ 测试库已执行
#   seed_knowledge_tree.py（9 学科 / 333 节点 / 292 父链接）；
# - e2e_ingestion 测试硬编码真实 DSN（验证真实入库文档 二中数学），不受本重定向影响。
# 关闭方式（需要连真实库跑时）：$env:AITUTOR_TEST_DB='0'; python -m pytest backend/tests


def _real_db_url() -> str:
    """取真实 DATABASE_URL：优先环境变量，其次 backend/.env（与全量跑法一致）。"""
    url = os.environ.get("DATABASE_URL", "")
    if url:
        return url
    env_path = Path(__file__).resolve().parents[1] / ".env"
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("DATABASE_URL="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return ""


def _test_db_url(real_url: str) -> str:
    """postgresql+asyncpg://user:pass@host:port/aitutors → …/aitutors_test"""
    return re.sub(r"/([^/?#]+)$", r"/\1_test", real_url)


def pytest_configure(config) -> None:
    WORKSPACE_TMP.mkdir(parents=True, exist_ok=True)
    config.option.basetemp = str(WORKSPACE_TMP)
    tempfile.tempdir = str(WORKSPACE_TMP)
    os.environ["TMPDIR"] = str(WORKSPACE_TMP)
    os.environ["TEMP"] = str(WORKSPACE_TMP)
    os.environ["TMP"] = str(WORKSPACE_TMP)

    # 默认路由到专用测试库（settings.database_url 首次实例化发生在测试模块
    # 导入阶段，晚于 pytest_configure，因此此处设置环境变量即可生效）。
    if os.environ.get("AITUTOR_TEST_DB", "1") == "1":
        real = _real_db_url()
        if real:
            os.environ["DATABASE_URL"] = _test_db_url(real)

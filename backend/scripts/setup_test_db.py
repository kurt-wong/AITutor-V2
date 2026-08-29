#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""建立专用测试库（幂等）：创建 <库名>_test → alembic upgrade head → 知识树种子 → 题型种子。

用法：
    python backend/scripts/setup_test_db.py
    # 或显式指定真实库 URL：
    $env:DATABASE_URL='postgresql+asyncpg://postgres:postgres@localhost:15432/aitutors'
    python backend/scripts/setup_test_db.py

说明：pytest（backend/tests/conftest.py）默认会把 DATABASE_URL 重定向到 <库名>_test，
本脚本保证该库存在且 schema/知识树/题型树就绪（新机器/新环境先跑本脚本再跑全量 pytest）。
"""
from __future__ import annotations

import asyncio
import os
import re
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
REAL_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:15432/aitutors",
)


def _asyncpg_dsn(url: str, dbname: str) -> str:
    """postgresql+asyncpg://u:p@h:port/db → postgresql://u:p@h:port/<dbname>"""
    return re.sub(r"/([^/?#]+)([?#].*)?$", f"/{dbname}\\2", re.sub(r"\+asyncpg", "", url))


async def main() -> None:
    import asyncpg

    test_db = re.search(r"/([^/?#]+)$", REAL_URL).group(1) + "_test"

    admin = await asyncpg.connect(_asyncpg_dsn(REAL_URL, "postgres"))
    try:
        exists = await admin.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", test_db
        )
        if not exists:
            await admin.execute(f'CREATE DATABASE "{test_db}"')
            print(f"created database: {test_db}")
        else:
            print(f"database exists: {test_db}")
    finally:
        await admin.close()

    test_url = re.sub(r"/([^/?#]+)$", f"/{test_db}", REAL_URL)
    env = {**os.environ, "DATABASE_URL": test_url}
    print("running: alembic upgrade head")
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND, env=env, check=True,
    )
    print("running: seed_knowledge_tree.py")
    subprocess.run(
        [sys.executable, "scripts/seed_knowledge_tree.py"],
        cwd=BACKEND, env=env, check=True,
    )
    print("running: seed_question_types")
    subprocess.run(
        [sys.executable, "-m", "app.domains.question_type_seed.seed"],
        cwd=BACKEND, env=env, check=True,
    )
    print("test db ready:", test_url)


asyncio.run(main())

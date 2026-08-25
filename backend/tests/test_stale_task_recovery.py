"""僵尸任务恢复单元测试（recover_stale_running_tasks）。

2026-08-25：worker 重启/崩溃遗留的 running 任务不会被轮询重新拾取
（worker 只查 queued）→ 文档永久卡 processing。此处验证：
- 超时 running（非 active）→ 重置 queued（清 progress/stage/error/result）
- active_task_id 豁免（正在处理的任务不被误恢复）
- 未超时的 running 不恢复
- 无僵尸时返回空列表
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.domains.task.service import TaskService


class _FakeRepo:
    """简化 repository：list_stale_running 返回配置好的任务列表。"""

    def __init__(self, stale_tasks):
        self.session = MagicMock()
        self.session.flush = AsyncMock()
        self._stale = stale_tasks

    async def list_stale_running(self, **kwargs):
        self.last_kwargs = kwargs
        return self._stale


def _make_task(status="running", progress="0.5", stage="llm_annotation"):
    t = MagicMock()
    t.id = uuid4()
    t.status = status
    t.progress = progress
    t.current_stage = stage
    t.error_detail = "old error"
    t.result_json = {"partial": True}
    return t


@pytest.mark.asyncio
async def test_recover_stale_running_resets_to_queued():
    """超时 running 任务 → 重置 queued，清空 progress/stage/error/result。"""
    stale = [_make_task()]
    repo = _FakeRepo(stale)
    service = TaskService(repo)

    recovered = await service.recover_stale_running_tasks(
        task_type="document_parse",
        active_task_id=None,
    )

    assert recovered == [stale[0].id]
    assert stale[0].status == "queued"
    assert stale[0].progress is None
    assert stale[0].current_stage is None
    assert stale[0].error_detail is None
    assert stale[0].result_json is None
    repo.session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_recover_skips_active_task():
    """当前 worker 正在处理的任务（active_task_id）不被恢复。"""
    stale = [_make_task()]
    repo = _FakeRepo(stale)
    service = TaskService(repo)

    # active_task_id 传入后，repository 负责过滤；这里验证参数正确传递
    await service.recover_stale_running_tasks(
        task_type="document_parse",
        active_task_id=uuid4(),
    )
    assert repo.last_kwargs["active_task_id"] is not None
    assert repo.last_kwargs["task_type"] == "document_parse"


@pytest.mark.asyncio
async def test_recover_no_stale_returns_empty():
    """无僵尸任务 → 返回空列表，不 flush。"""
    repo = _FakeRepo([])
    service = TaskService(repo)

    recovered = await service.recover_stale_running_tasks(
        task_type="document_parse",
        active_task_id=None,
    )

    assert recovered == []
    repo.session.flush.assert_not_awaited()

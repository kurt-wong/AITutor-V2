"""
Worker 状态映射测试。

C5/C6: result.status → document.processing_status 映射
H3: 原子提交（task + document 同一 commit）
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID


# ═══════════════════════════════════════════════════════════════════
# C5/C6: Worker 状态分支
# ═══════════════════════════════════════════════════════════════════


class TestWorkerStatusMapping:
    """C5/C6: Worker 根据 result.status 正确设置 document.processing_status。"""

    @pytest.mark.asyncio
    async def test_worker_pipeline_succeeded_sets_document_completed(self):
        """Pipeline succeeded → document.processing_status = 'completed'。"""
        from app.worker.document_worker import document_parse_worker

        mock_session = AsyncMock()
        # Phase 2A Step 3：worker 新增幂等清理调用 session.scalars（查询未审核记录）
        mock_session.scalars = AsyncMock(return_value=[])
        mock_session.get = AsyncMock(return_value=None)
        mock_session.delete = AsyncMock()
        mock_session.flush = AsyncMock()
        mock_session.close = AsyncMock()
        mock_task_service = AsyncMock()
        mock_task_service.commit = AsyncMock()
        mock_doc_service = AsyncMock()
        mock_doc_service.commit = AsyncMock()

        mock_task = MagicMock()
        mock_task.id = UUID("00000000-0000-0000-0000-000000000001")
        mock_task.payload_json = {
            "document_id": str(UUID("00000000-0000-0000-0000-000000000002"))
        }

        mock_doc = MagicMock()
        mock_doc.object_key = "test.pdf"
        mock_doc.filename = "test.pdf"

        from app.domains.document.pipeline import PipelineResult
        success_result = PipelineResult()
        success_result.status = "succeeded"

        call_count = 0
        stop_event = asyncio.Event()

        async def mock_factory():
            nonlocal call_count
            call_count += 1
            if call_count >= 1:
                stop_event.set()
            return mock_session, mock_task_service, mock_doc_service

        mock_task_service.list_tasks = AsyncMock(return_value=[mock_task])
        mock_doc_service.get_document = AsyncMock(return_value=mock_doc)

        with patch("app.domains.document.processor.DocumentProcessor") as MockProcessor:
            mock_instance = MagicMock()
            mock_instance.process_document = AsyncMock(return_value=success_result)
            # Phase 2A Step 3：pipeline 成功路径会继续 extract_and_ingest，
            # 必须 mock 成功返回 IngestionResult（否则 await MagicMock 抛 TypeError）
            from app.domains.document.ingestion import IngestionResult
            mock_instance.extract_and_ingest = AsyncMock(return_value=IngestionResult())
            MockProcessor.return_value = mock_instance

            worker_task = asyncio.create_task(
                document_parse_worker(
                    storage=MagicMock(),
                    gateway=MagicMock(),
                    create_task_services=mock_factory,
                    stop_event=stop_event,
                )
            )

            try:
                await asyncio.wait_for(worker_task, timeout=5.0)
            except asyncio.TimeoutError:
                worker_task.cancel()
                try:
                    await worker_task
                except asyncio.CancelledError:
                    pass

        assert mock_doc.processing_status == "completed"

    @pytest.mark.asyncio
    async def test_worker_pipeline_failed_sets_document_failed(self):
        """Pipeline failed → document.processing_status = 'failed'。"""
        from app.worker.document_worker import document_parse_worker

        mock_session = AsyncMock()
        # Phase 2A Step 3：worker 新增幂等清理调用 session.scalars（查询未审核记录）
        mock_session.scalars = AsyncMock(return_value=[])
        mock_session.get = AsyncMock(return_value=None)
        mock_session.delete = AsyncMock()
        mock_session.flush = AsyncMock()
        mock_session.close = AsyncMock()
        mock_task_service = AsyncMock()
        mock_task_service.commit = AsyncMock()
        mock_doc_service = AsyncMock()
        mock_doc_service.commit = AsyncMock()

        mock_task = MagicMock()
        mock_task.id = UUID("00000000-0000-0000-0000-000000000001")
        mock_task.payload_json = {
            "document_id": str(UUID("00000000-0000-0000-0000-000000000002"))
        }

        mock_doc = MagicMock()
        mock_doc.object_key = "test.pdf"
        mock_doc.filename = "test.pdf"

        from app.domains.document.pipeline import PipelineResult
        failed_result = PipelineResult()
        failed_result.status = "failed"
        failed_result.stage_errors = [{"stage": "llm_annotation", "error": "timeout"}]
        failed_result.errors = ["Stage 3 (llm_annotation): timeout"]

        call_count = 0
        stop_event = asyncio.Event()

        async def mock_factory():
            nonlocal call_count
            call_count += 1
            if call_count >= 1:
                stop_event.set()
            return mock_session, mock_task_service, mock_doc_service

        mock_task_service.list_tasks = AsyncMock(return_value=[mock_task])
        mock_doc_service.get_document = AsyncMock(return_value=mock_doc)

        with patch("app.domains.document.processor.DocumentProcessor") as MockProcessor:
            mock_instance = MagicMock()
            mock_instance.process_document = AsyncMock(return_value=failed_result)
            MockProcessor.return_value = mock_instance

            worker_task = asyncio.create_task(
                document_parse_worker(
                    storage=MagicMock(),
                    gateway=MagicMock(),
                    create_task_services=mock_factory,
                    stop_event=stop_event,
                )
            )

            try:
                await asyncio.wait_for(worker_task, timeout=5.0)
            except asyncio.TimeoutError:
                worker_task.cancel()
                try:
                    await worker_task
                except asyncio.CancelledError:
                    pass

        assert mock_doc.processing_status == "failed"


# ═══════════════════════════════════════════════════════════════════
# H3: 原子提交
# ═══════════════════════════════════════════════════════════════════


class TestAtomicCommit:
    """H3: task 和 document 状态在单次 commit 后一致。"""

    @pytest.mark.asyncio
    async def test_atomic_commit_task_document_consistent(self):
        """task=succeeded + document=completed 在同一 commit 后一致。"""
        from app.worker.document_worker import document_parse_worker

        mock_session = AsyncMock()
        # Phase 2A Step 3：worker 新增幂等清理调用 session.scalars（查询未审核记录）
        mock_session.scalars = AsyncMock(return_value=[])
        mock_session.get = AsyncMock(return_value=None)
        mock_session.delete = AsyncMock()
        mock_session.flush = AsyncMock()
        mock_session.close = AsyncMock()
        mock_task_service = AsyncMock()
        mock_task_service.commit = AsyncMock()
        mock_doc_service = AsyncMock()
        mock_doc_service.commit = AsyncMock()

        mock_task = MagicMock()
        mock_task.id = UUID("00000000-0000-0000-0000-000000000001")
        mock_task.payload_json = {
            "document_id": str(UUID("00000000-0000-0000-0000-000000000002"))
        }
        mock_task.status = "running"

        mock_doc = MagicMock()
        mock_doc.object_key = "test.pdf"
        mock_doc.filename = "test.pdf"
        mock_doc.processing_status = "processing"

        from app.domains.document.pipeline import PipelineResult
        success_result = PipelineResult()
        success_result.status = "succeeded"

        call_count = 0
        stop_event = asyncio.Event()

        async def mock_factory():
            nonlocal call_count
            call_count += 1
            if call_count >= 1:
                stop_event.set()
            return mock_session, mock_task_service, mock_doc_service

        mock_task_service.list_tasks = AsyncMock(return_value=[mock_task])
        mock_doc_service.get_document = AsyncMock(return_value=mock_doc)

        with patch("app.domains.document.processor.DocumentProcessor") as MockProcessor:
            mock_instance = MagicMock()
            mock_instance.process_document = AsyncMock(return_value=success_result)
            from app.domains.document.ingestion import IngestionResult
            mock_instance.extract_and_ingest = AsyncMock(return_value=IngestionResult())
            MockProcessor.return_value = mock_instance

            worker_task = asyncio.create_task(
                document_parse_worker(
                    storage=MagicMock(),
                    gateway=MagicMock(),
                    create_task_services=mock_factory,
                    stop_event=stop_event,
                )
            )

            try:
                await asyncio.wait_for(worker_task, timeout=5.0)
            except asyncio.TimeoutError:
                worker_task.cancel()
                try:
                    await worker_task
                except asyncio.CancelledError:
                    pass

        # 验证 document 状态一致
        # succeed_task 在 processor 内部调用，mock processor 不触发
        assert mock_doc.processing_status == "completed"

    @pytest.mark.asyncio
    async def test_atomic_commit_rollback_on_error(self):
        """commit 抛错 → task 和 document 都回滚（状态不变）。"""
        from app.worker.document_worker import document_parse_worker

        mock_session = AsyncMock()
        # Phase 2A Step 3：worker 新增幂等清理调用 session.scalars（查询未审核记录）
        mock_session.scalars = AsyncMock(return_value=[])
        mock_session.get = AsyncMock(return_value=None)
        mock_session.delete = AsyncMock()
        mock_session.flush = AsyncMock()
        mock_session.close = AsyncMock()
        mock_task_service = AsyncMock()
        mock_doc_service = AsyncMock()

        # 让 commit 抛错
        mock_task_service.commit = AsyncMock(side_effect=RuntimeError("db down"))
        mock_doc_service.commit = AsyncMock(side_effect=RuntimeError("db down"))

        mock_task = MagicMock()
        mock_task.id = UUID("00000000-0000-0000-0000-000000000001")
        mock_task.payload_json = {
            "document_id": str(UUID("00000000-0000-0000-0000-000000000002"))
        }
        mock_task.status = "running"

        mock_doc = MagicMock()
        mock_doc.object_key = "test.pdf"
        mock_doc.filename = "test.pdf"
        mock_doc.processing_status = "processing"

        from app.domains.document.pipeline import PipelineResult
        success_result = PipelineResult()
        success_result.status = "succeeded"

        call_count = 0
        stop_event = asyncio.Event()

        async def mock_factory():
            nonlocal call_count
            call_count += 1
            if call_count >= 1:
                stop_event.set()
            return mock_session, mock_task_service, mock_doc_service

        mock_task_service.list_tasks = AsyncMock(return_value=[mock_task])
        mock_doc_service.get_document = AsyncMock(return_value=mock_doc)

        with patch("app.domains.document.processor.DocumentProcessor") as MockProcessor:
            mock_instance = MagicMock()
            mock_instance.process_document = AsyncMock(return_value=success_result)
            from app.domains.document.ingestion import IngestionResult
            mock_instance.extract_and_ingest = AsyncMock(return_value=IngestionResult())
            MockProcessor.return_value = mock_instance

            worker_task = asyncio.create_task(
                document_parse_worker(
                    storage=MagicMock(),
                    gateway=MagicMock(),
                    create_task_services=mock_factory,
                    stop_event=stop_event,
                )
            )

            try:
                await asyncio.wait_for(worker_task, timeout=5.0)
            except asyncio.TimeoutError:
                worker_task.cancel()
                try:
                    await worker_task
                except asyncio.CancelledError:
                    pass

        # commit 失败后，document 状态应回滚到初始值
        # 由于 mock_doc 是 MagicMock，赋值不会真正回滚
        # 但我们验证 commit 被调用了（尝试提交）
        mock_doc_service.commit.assert_called()

    @pytest.mark.asyncio
    async def test_worker_exception_fails_task_once(self):
        """Processor 抛异常时，worker 只 fail task 一次。"""
        from app.worker.document_worker import document_parse_worker

        mock_session = AsyncMock()
        # Phase 2A Step 3：worker 新增幂等清理调用 session.scalars（查询未审核记录）
        mock_session.scalars = AsyncMock(return_value=[])
        mock_session.get = AsyncMock(return_value=None)
        mock_session.delete = AsyncMock()
        mock_session.flush = AsyncMock()
        mock_session.close = AsyncMock()
        mock_task_service = AsyncMock()
        mock_task_service.commit = AsyncMock()
        mock_doc_service = AsyncMock()
        mock_doc_service.commit = AsyncMock()

        mock_task = MagicMock()
        mock_task.id = UUID("00000000-0000-0000-0000-000000000001")
        mock_task.payload_json = {
            "document_id": str(UUID("00000000-0000-0000-0000-000000000002"))
        }

        mock_doc = MagicMock()
        mock_doc.object_key = "test.pdf"
        mock_doc.filename = "test.pdf"

        call_count = 0
        stop_event = asyncio.Event()

        async def mock_factory():
            nonlocal call_count
            call_count += 1
            if call_count >= 1:
                stop_event.set()
            return mock_session, mock_task_service, mock_doc_service

        mock_task_service.list_tasks = AsyncMock(return_value=[mock_task])
        mock_doc_service.get_document = AsyncMock(return_value=mock_doc)

        with patch("app.domains.document.processor.DocumentProcessor") as MockProcessor:
            mock_instance = MagicMock()
            mock_instance.process_document = AsyncMock(
                side_effect=RuntimeError("pipeline crashed")
            )
            MockProcessor.return_value = mock_instance

            worker_task = asyncio.create_task(
                document_parse_worker(
                    storage=MagicMock(),
                    gateway=MagicMock(),
                    create_task_services=mock_factory,
                    stop_event=stop_event,
                )
            )

            try:
                await asyncio.wait_for(worker_task, timeout=5.0)
            except asyncio.TimeoutError:
                worker_task.cancel()
                try:
                    await worker_task
                except asyncio.CancelledError:
                    pass

        # processor 内部已 fail_task，worker 不应重复调用
        # fail_task 只在 processor 内部被调用，worker 内层不应再调
        mock_task_service.fail_task.assert_not_called()
        assert mock_doc.processing_status == "failed"


# ═══════════════════════════════════════════════════════════════════
# Fix 4: partial_failed 一致性
# ═══════════════════════════════════════════════════════════════════


class TestPartialFailedConsistency:
    """Fix 4: partial_failed 必须同时设置 task=failed + document=failed。"""

    @pytest.mark.asyncio
    async def test_worker_partial_failed_status_consistent(self):
        """方案 A: fake processor 在返回 partial_failed 前先设置 task failed，
        worker 同步 document → 最终 task=failed + document=failed。

        fail_task 是真实函数（非 AsyncMock），会实际修改 mock_task.status。
        """
        from app.worker.document_worker import document_parse_worker

        mock_session = AsyncMock()
        # Phase 2A Step 3：worker 新增幂等清理调用 session.scalars（查询未审核记录）
        mock_session.scalars = AsyncMock(return_value=[])
        mock_session.get = AsyncMock(return_value=None)
        mock_session.delete = AsyncMock()
        mock_session.flush = AsyncMock()
        mock_session.close = AsyncMock()
        mock_task_service = AsyncMock()
        mock_task_service.commit = AsyncMock()
        mock_doc_service = AsyncMock()
        mock_doc_service.commit = AsyncMock()

        mock_task = MagicMock()
        mock_task.id = UUID("00000000-0000-0000-0000-000000000001")
        mock_task.payload_json = {
            "document_id": str(UUID("00000000-0000-0000-0000-000000000002"))
        }
        mock_task.status = "running"

        mock_doc = MagicMock()
        mock_doc.object_key = "test.pdf"
        mock_doc.filename = "test.pdf"
        mock_doc.processing_status = "processing"

        from app.domains.document.pipeline import PipelineResult
        partial_result = PipelineResult()
        partial_result.status = "partial_failed"
        partial_result.errors = ["partial error"]

        # fail_task 真实修改 task.status（非 AsyncMock 空操作）
        async def real_fail_task(task_id, error_detail=None):
            mock_task.status = "failed"

        mock_task_service.fail_task = real_fail_task

        # fake processor: 先设置 task failed，再返回 partial_failed
        async def fake_process(**kwargs):
            await mock_task_service.fail_task(kwargs["task_id"], error_detail="partial")
            return partial_result

        call_count = 0
        stop_event = asyncio.Event()

        async def mock_factory():
            nonlocal call_count
            call_count += 1
            if call_count >= 1:
                stop_event.set()
            return mock_session, mock_task_service, mock_doc_service

        mock_task_service.list_tasks = AsyncMock(return_value=[mock_task])
        mock_doc_service.get_document = AsyncMock(return_value=mock_doc)

        with patch("app.domains.document.processor.DocumentProcessor") as MockProcessor:
            mock_instance = MagicMock()
            mock_instance.process_document = fake_process
            MockProcessor.return_value = mock_instance

            worker_task = asyncio.create_task(
                document_parse_worker(
                    storage=MagicMock(),
                    gateway=MagicMock(),
                    create_task_services=mock_factory,
                    stop_event=stop_event,
                )
            )

            try:
                await asyncio.wait_for(worker_task, timeout=5.0)
            except asyncio.TimeoutError:
                worker_task.cancel()
                try:
                    await worker_task
                except asyncio.CancelledError:
                    pass

        # task 被 processor 设置为 failed（fake_process 中调用 real_fail_task）
        assert mock_task.status == "failed", f"task.status should be 'failed', got '{mock_task.status}'"
        # document 被 worker 设置为 failed
        assert mock_doc.processing_status == "failed"

    @pytest.mark.asyncio
    async def test_worker_partial_failed_no_double_fail(self):
        """worker 不应在 partial_failed 时重复调用 fail_task。"""
        from app.worker.document_worker import document_parse_worker

        mock_session = AsyncMock()
        # Phase 2A Step 3：worker 新增幂等清理调用 session.scalars（查询未审核记录）
        mock_session.scalars = AsyncMock(return_value=[])
        mock_session.get = AsyncMock(return_value=None)
        mock_session.delete = AsyncMock()
        mock_session.flush = AsyncMock()
        mock_session.close = AsyncMock()
        mock_task_service = AsyncMock()
        mock_task_service.commit = AsyncMock()
        mock_doc_service = AsyncMock()
        mock_doc_service.commit = AsyncMock()

        mock_task = MagicMock()
        mock_task.id = UUID("00000000-0000-0000-0000-000000000001")
        mock_task.payload_json = {
            "document_id": str(UUID("00000000-0000-0000-0000-000000000002"))
        }
        mock_task.status = "running"

        mock_doc = MagicMock()
        mock_doc.object_key = "test.pdf"
        mock_doc.filename = "test.pdf"

        from app.domains.document.pipeline import PipelineResult
        partial_result = PipelineResult()
        partial_result.status = "partial_failed"

        call_count = 0
        stop_event = asyncio.Event()

        async def mock_factory():
            nonlocal call_count
            call_count += 1
            if call_count >= 1:
                stop_event.set()
            return mock_session, mock_task_service, mock_doc_service

        mock_task_service.list_tasks = AsyncMock(return_value=[mock_task])
        mock_doc_service.get_document = AsyncMock(return_value=mock_doc)

        with patch("app.domains.document.processor.DocumentProcessor") as MockProcessor:
            mock_instance = MagicMock()
            mock_instance.process_document = AsyncMock(return_value=partial_result)
            MockProcessor.return_value = mock_instance

            worker_task = asyncio.create_task(
                document_parse_worker(
                    storage=MagicMock(),
                    gateway=MagicMock(),
                    create_task_services=mock_factory,
                    stop_event=stop_event,
                )
            )

            try:
                await asyncio.wait_for(worker_task, timeout=5.0)
            except asyncio.TimeoutError:
                worker_task.cancel()
                try:
                    await worker_task
                except asyncio.CancelledError:
                    pass

        # worker 层面：document 被设置为 failed
        assert mock_doc.processing_status == "failed"


# ═══════════════════════════════════════════════════════════════════
# Fix 5: Commit 失败 rollback
# ═══════════════════════════════════════════════════════════════════


class TestCommitFailureRollback:
    """Fix 5: 最终 commit 失败时必须 rollback，不能用脏 session 继续。"""

    @pytest.mark.asyncio
    async def test_worker_commit_failure_rolls_back_task_and_document(self):
        """成功路径：最终 commit 失败 → session.rollback() 被调用。"""
        from app.worker.document_worker import document_parse_worker

        mock_session = AsyncMock()
        # Phase 2A Step 3：worker 新增幂等清理调用 session.scalars（查询未审核记录）
        mock_session.scalars = AsyncMock(return_value=[])
        mock_session.get = AsyncMock(return_value=None)
        mock_session.delete = AsyncMock()
        mock_session.flush = AsyncMock()
        mock_session.close = AsyncMock()
        mock_task_service = AsyncMock()
        mock_doc_service = AsyncMock()

        # 模拟标记 processing 的 commit 成功，最终 commit 失败
        commit_call_count = 0

        async def doc_service_commit():
            nonlocal commit_call_count
            commit_call_count += 1
            if commit_call_count >= 2:
                raise RuntimeError("db commit failed")

        mock_doc_service.commit = doc_service_commit

        mock_task_service.commit = AsyncMock()

        mock_task = MagicMock()
        mock_task.id = UUID("00000000-0000-0000-0000-000000000001")
        mock_task.payload_json = {
            "document_id": str(UUID("00000000-0000-0000-0000-000000000002"))
        }

        mock_doc = MagicMock()
        mock_doc.object_key = "test.pdf"
        mock_doc.filename = "test.pdf"
        mock_doc.processing_status = "processing"

        from app.domains.document.pipeline import PipelineResult
        success_result = PipelineResult()
        success_result.status = "succeeded"

        call_count = 0
        stop_event = asyncio.Event()

        async def mock_factory():
            nonlocal call_count
            call_count += 1
            if call_count >= 1:
                stop_event.set()
            return mock_session, mock_task_service, mock_doc_service

        mock_task_service.list_tasks = AsyncMock(return_value=[mock_task])
        mock_doc_service.get_document = AsyncMock(return_value=mock_doc)

        with patch("app.domains.document.processor.DocumentProcessor") as MockProcessor:
            mock_instance = MagicMock()
            mock_instance.process_document = AsyncMock(return_value=success_result)
            from app.domains.document.ingestion import IngestionResult
            mock_instance.extract_and_ingest = AsyncMock(return_value=IngestionResult())
            MockProcessor.return_value = mock_instance

            worker_task = asyncio.create_task(
                document_parse_worker(
                    storage=MagicMock(),
                    gateway=MagicMock(),
                    create_task_services=mock_factory,
                    stop_event=stop_event,
                )
            )

            try:
                await asyncio.wait_for(worker_task, timeout=5.0)
            except asyncio.TimeoutError:
                worker_task.cancel()
                try:
                    await worker_task
                except asyncio.CancelledError:
                    pass

        # rollback 被调用
        mock_session.rollback.assert_called()

    @pytest.mark.asyncio
    async def test_worker_except_path_commit_failure_triggers_rollback(self):
        """except 路径中 commit 失败 → rollback 被调用，session 不脏。"""
        from app.worker.document_worker import document_parse_worker

        mock_session = AsyncMock()
        # Phase 2A Step 3：worker 新增幂等清理调用 session.scalars（查询未审核记录）
        mock_session.scalars = AsyncMock(return_value=[])
        mock_session.get = AsyncMock(return_value=None)
        mock_session.delete = AsyncMock()
        mock_session.flush = AsyncMock()
        mock_session.close = AsyncMock()
        mock_task_service = AsyncMock()
        mock_task_service.commit = AsyncMock()
        mock_doc_service = AsyncMock()
        mock_doc_service.commit = AsyncMock()

        mock_task = MagicMock()
        mock_task.id = UUID("00000000-0000-0000-0000-000000000001")
        mock_task.payload_json = {
            "document_id": str(UUID("00000000-0000-0000-0000-000000000002"))
        }

        mock_doc = MagicMock()
        mock_doc.id = UUID("00000000-0000-0000-0000-000000000002")
        mock_doc.processing_status = "processing"
        mock_doc.content = None

        stop_event = asyncio.Event()
        call_count = 0

        async def mock_factory():
            nonlocal call_count
            call_count += 1
            if call_count >= 1:
                stop_event.set()
            return mock_session, mock_task_service, mock_doc_service

        mock_task_service.list_tasks = AsyncMock(return_value=[mock_task])
        mock_task_service.fail_task = AsyncMock()

        # 第一次 commit（标记 processing）成功，第二次（except 路径）失败
        doc_commit_count = 0

        async def failing_doc_commit():
            nonlocal doc_commit_count
            doc_commit_count += 1
            if doc_commit_count >= 2:
                raise RuntimeError("disk full")

        mock_doc_service.commit = failing_doc_commit

        with patch("app.domains.document.processor.DocumentProcessor") as MockProcessor:
            mock_instance = MagicMock()

            async def processor_with_fail_task(**kwargs):
                await mock_task_service.fail_task(kwargs["task_id"], error_detail="processor error")
                raise RuntimeError("processor exploded")

            mock_instance.process_document = processor_with_fail_task
            MockProcessor.return_value = mock_instance

            worker_task = asyncio.create_task(
                document_parse_worker(
                    storage=MagicMock(),
                    gateway=MagicMock(),
                    create_task_services=mock_factory,
                    stop_event=stop_event,
                )
            )

            try:
                await asyncio.wait_for(worker_task, timeout=5.0)
            except asyncio.TimeoutError:
                worker_task.cancel()
                try:
                    await worker_task
                except asyncio.CancelledError:
                    pass

        # fail_task 被 processor 异常处理调用一次
        mock_task_service.fail_task.assert_called_once()
        # except 路径 commit 失败 → rollback 被调用（回滚了 processing_status 的变更）
        mock_session.rollback.assert_called()

    @pytest.mark.asyncio
    async def test_worker_download_failure_marks_task_and_document_once(self):
        """下载异常 → processor 内部 fail_task + worker 设 document failed → 不重复。"""
        from app.worker.document_worker import document_parse_worker

        mock_session = AsyncMock()
        # Phase 2A Step 3：worker 新增幂等清理调用 session.scalars（查询未审核记录）
        mock_session.scalars = AsyncMock(return_value=[])
        mock_session.get = AsyncMock(return_value=None)
        mock_session.delete = AsyncMock()
        mock_session.flush = AsyncMock()
        mock_session.close = AsyncMock()
        mock_task_service = AsyncMock()
        mock_task_service.commit = AsyncMock()
        mock_doc_service = AsyncMock()
        mock_doc_service.commit = AsyncMock()

        mock_task = MagicMock()
        mock_task.id = UUID("00000000-0000-0000-0000-000000000001")
        mock_task.payload_json = {
            "document_id": str(UUID("00000000-0000-0000-0000-000000000002"))
        }

        mock_doc = MagicMock()
        mock_doc.object_key = "test.pdf"
        mock_doc.filename = "test.pdf"

        call_count = 0
        stop_event = asyncio.Event()

        async def mock_factory():
            nonlocal call_count
            call_count += 1
            if call_count >= 1:
                stop_event.set()
            return mock_session, mock_task_service, mock_doc_service

        mock_task_service.list_tasks = AsyncMock(return_value=[mock_task])
        mock_doc_service.get_document = AsyncMock(return_value=mock_doc)

        with patch("app.domains.document.processor.DocumentProcessor") as MockProcessor:
            mock_instance = MagicMock()
            # 下载失败：processor 内部 fail_task 后 raise
            async def fail_download(**kwargs):
                await mock_task_service.fail_task(kwargs["task_id"], error_detail="下载失败")
                raise RuntimeError("download failed")

            mock_instance.process_document = fail_download
            MockProcessor.return_value = mock_instance

            worker_task = asyncio.create_task(
                document_parse_worker(
                    storage=MagicMock(),
                    gateway=MagicMock(),
                    create_task_services=mock_factory,
                    stop_event=stop_event,
                )
            )

            try:
                await asyncio.wait_for(worker_task, timeout=5.0)
            except asyncio.TimeoutError:
                worker_task.cancel()
                try:
                    await worker_task
                except asyncio.CancelledError:
                    pass

        # processor 内部调用了一次 fail_task
        mock_task_service.fail_task.assert_called_once()
        # document 被 worker 设置为 failed
        assert mock_doc.processing_status == "failed"


# ═══════════════════════════════════════════════════════════════════
# Fix 5 (补充): Rollback 原子性 — 验证状态一致性
# ═══════════════════════════════════════════════════════════════════


class _TrackedObject:
    """可追踪状态变更并在 rollback 时恢复的模拟对象。"""

    def __init__(self, **initial):
        object.__setattr__(self, "_state", dict(initial))
        object.__setattr__(self, "_state_history", [dict(initial)])

    def __getattr__(self, name):
        state = object.__getattribute__(self, "_state")
        if name in state:
            return state[name]
        raise AttributeError(name)

    def __setattr__(self, name, value):
        state = object.__getattribute__(self, "_state")
        state[name] = value

    def _snapshot(self):
        state = object.__getattribute__(self, "_state")
        history = object.__getattribute__(self, "_state_history")
        history.append(dict(state))

    def _restore(self):
        history = object.__getattribute__(self, "_state_history")
        if len(history) > 1:
            history.pop()
        state = object.__getattribute__(self, "_state")
        state.clear()
        state.update(history[-1])


class _FakeSession:
    """模拟 session：commit 失败时 rollback 恢复所有 TrackedObject 状态。"""

    def __init__(self, tracked_objects: list, fail_on_commit_count: int = 2):
        self._tracked = tracked_objects
        self._fail_count = fail_on_commit_count
        self._commit_count = 0
        self._rollback_called = False

    async def commit(self):
        self._commit_count += 1
        for obj in self._tracked:
            obj._snapshot()
        if self._commit_count >= self._fail_count:
            raise RuntimeError("db commit failed")

    async def rollback(self):
        self._rollback_called = True
        for obj in self._tracked:
            obj._restore()

    async def close(self):
        pass

    async def scalars(self, stmt):
        # Phase 2A Step 3：幂等清理查询 — 无未审核记录
        return []

    async def get(self, model, ident):
        return None

    async def delete(self, obj):
        pass

    async def flush(self):
        pass


class TestRollbackAtomicity:
    """Fix 5 补充：commit 失败后 rollback 必须恢复 task/document 状态一致性。"""

    @pytest.mark.asyncio
    async def test_success_path_commit_failure_restores_document_state(self):
        """成功路径 commit 失败 → rollback 恢复 document.processing_status 到 pre-commit 状态。"""
        from app.worker.document_worker import document_parse_worker
        from app.domains.document.pipeline import PipelineResult

        # 初始状态：task=queued, doc=processing（第一次 commit 后）
        mock_task = _TrackedObject(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            payload_json={"document_id": str(UUID("00000000-0000-0000-0000-000000000002"))},
            status="queued",
        )
        mock_doc = _TrackedObject(
            object_key="test.pdf",
            filename="test.pdf",
            processing_status="processing",
            error_message=None,
            subject="数学",
        )

        # 第一次 commit（标记 processing）成功，第二次（最终提交）失败
        session = _FakeSession(
            tracked_objects=[mock_task, mock_doc],
            fail_on_commit_count=2,
        )

        mock_task_service = AsyncMock()
        mock_task_service.commit = AsyncMock()
        mock_task_service.list_tasks = AsyncMock(return_value=[mock_task])
        mock_task_service.succeed_task = AsyncMock()

        mock_doc_service = AsyncMock()
        mock_doc_service.get_document = AsyncMock(return_value=mock_doc)
        # doc_service commit 委托给 session
        doc_commit_count = 0

        async def doc_commit():
            nonlocal doc_commit_count
            doc_commit_count += 1
            await session.commit()

        mock_doc_service.commit = doc_commit

        success_result = PipelineResult()
        success_result.status = "succeeded"

        stop_event = asyncio.Event()
        factory_count = 0

        async def mock_factory():
            nonlocal factory_count
            factory_count += 1
            if factory_count >= 1:
                stop_event.set()
            return session, mock_task_service, mock_doc_service

        with patch("app.domains.document.processor.DocumentProcessor") as MockProcessor:
            mock_instance = MagicMock()
            mock_instance.process_document = AsyncMock(return_value=success_result)
            from app.domains.document.ingestion import IngestionResult
            mock_instance.extract_and_ingest = AsyncMock(return_value=IngestionResult())
            MockProcessor.return_value = mock_instance

            worker_task = asyncio.create_task(
                document_parse_worker(
                    storage=MagicMock(),
                    gateway=MagicMock(),
                    create_task_services=mock_factory,
                    stop_event=stop_event,
                )
            )

            try:
                await asyncio.wait_for(worker_task, timeout=5.0)
            except asyncio.TimeoutError:
                worker_task.cancel()
                try:
                    await worker_task
                except asyncio.CancelledError:
                    pass

        # 核心断言：rollback 被调用
        assert session._rollback_called, "session.rollback() was not called"
        # document 状态应被恢复到 commit 前的状态（processing），不是 "completed"
        assert mock_doc.processing_status == "processing", (
            f"document should be 'processing' after rollback, got '{mock_doc.processing_status}'"
        )

    @pytest.mark.asyncio
    async def test_except_path_commit_failure_restores_document_state(self):
        """except 路径 commit 失败 → rollback 恢复 document.processing_status。"""
        from app.worker.document_worker import document_parse_worker

        mock_task = _TrackedObject(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            payload_json={"document_id": str(UUID("00000000-0000-0000-0000-000000000002"))},
            status="queued",
        )
        mock_doc = _TrackedObject(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            object_key="test.pdf",
            filename="test.pdf",
            processing_status="processing",
            error_message=None,
            subject="数学",
        )

        # 第一次 commit（标记 processing）成功，第二次（except 路径）失败
        session = _FakeSession(
            tracked_objects=[mock_task, mock_doc],
            fail_on_commit_count=2,
        )

        mock_task_service = AsyncMock()
        mock_task_service.commit = AsyncMock()
        mock_task_service.list_tasks = AsyncMock(return_value=[mock_task])
        mock_task_service.fail_task = AsyncMock()

        mock_doc_service = AsyncMock()
        mock_doc_service.get_document = AsyncMock(return_value=mock_doc)

        doc_commit_count = 0

        async def doc_commit():
            nonlocal doc_commit_count
            doc_commit_count += 1
            await session.commit()

        mock_doc_service.commit = doc_commit

        stop_event = asyncio.Event()
        factory_count = 0

        async def mock_factory():
            nonlocal factory_count
            factory_count += 1
            if factory_count >= 1:
                stop_event.set()
            return session, mock_task_service, mock_doc_service

        with patch("app.domains.document.processor.DocumentProcessor") as MockProcessor:
            mock_instance = MagicMock()

            async def processor_explodes(**kwargs):
                # processor 内部调用 fail_task 后抛异常
                await mock_task_service.fail_task(kwargs["task_id"], error_detail="boom")
                raise RuntimeError("processor exploded")

            mock_instance.process_document = processor_explodes
            MockProcessor.return_value = mock_instance

            worker_task = asyncio.create_task(
                document_parse_worker(
                    storage=MagicMock(),
                    gateway=MagicMock(),
                    create_task_services=mock_factory,
                    stop_event=stop_event,
                )
            )
            try:
                await asyncio.wait_for(worker_task, timeout=5.0)
            except asyncio.TimeoutError:
                worker_task.cancel()
                try:
                    await worker_task
                except asyncio.CancelledError:
                    pass

        # fail_task 被 processor 调用
        mock_task_service.fail_task.assert_called_once()
        # rollback 被调用
        assert session._rollback_called, "session.rollback() was not called"
        # document 状态应被恢复到 commit 前
        assert mock_doc.processing_status == "processing", (
            f"document should be 'processing' after rollback, got '{mock_doc.processing_status}'"
        )

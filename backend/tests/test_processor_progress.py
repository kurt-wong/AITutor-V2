"""
C7/H4/Fix 8: Processor 进度回调集成测试。

验证真实 run_pipeline 通过 progress_callback 发出所有关键阶段，
且 DocumentProcessor.get_progress_callback() 正确转发到 task_service.update_progress。
"""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

from app.domains.document.pipeline import PipelineResult
from app.domains.document.schemas_l1 import L1Document, L1Line, L1Page
from app.domains.document.schemas_l2 import (
    L2DocumentAnnotation,
    L2QuestionAnnotation,
    CorrectedAnchor,
)


def _make_l1_doc() -> L1Document:
    """构造最小 L1Document。"""
    lines = [
        L1Line("P1L001", 1, 1, 1, "1. 测试题干", "text"),
        L1Line("P1L002", 1, 2, 2, "（A）选项A", "text"),
        L1Line("P1L003", 1, 3, 3, "（B）选项B", "text"),
    ]
    return L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source="native",
        total_pages=1,
    )


def _make_annotation() -> L2DocumentAnnotation:
    """构造最小 L2DocumentAnnotation。"""
    return L2DocumentAnnotation(
        filename="test.pdf",
        questions=[
            L2QuestionAnnotation(
                question_number="1",
                question_type="single_choice",
                stem_line_ids=["P1L001"],
                options_line_ids={"A": ["P1L002"], "B": ["P1L003"]},
                source_page=1,
            ),
        ],
        corrected_anchors=[
            CorrectedAnchor(
                field="stem",
                llm_line_ids=["P1L001"],
                corrected_line_ids=["P1L001"],
                anchor_status="exact",
            ),
        ],
        anchor_status_summary={"exact": 1},
    )


class TestProcessorProgressRealPipeline:
    """Fix 8: 用真实 run_pipeline 验证 progress_callback 阶段覆盖。

    策略：wrap 真实 run_pipeline，在调用前后拦截 progress_callback，
    同时 mock 掉 I/O 和 LLM 依赖。
    """

    @pytest.mark.asyncio
    async def test_real_pipeline_emits_all_progress_stages(self):
        """真实 run_pipeline 通过 progress_callback 发出所有关键阶段。"""
        from app.domains.document.processor import DocumentProcessor
        from app.domains.document import simple_pipeline as pipeline_mod

        mock_task_service = AsyncMock()
        mock_task_service.commit = AsyncMock()
        mock_storage = MagicMock()
        mock_gateway = MagicMock()

        # 记录所有 update_progress 调用
        progress_calls = []
        task_stages = {}

        async def track_progress(task_id, progress=None, stage=None):
            progress_calls.append({"progress": progress, "stage": stage})
            if stage:
                task_stages[str(task_id)] = stage

        mock_task_service.update_progress = track_progress

        # 拦截 processor 的 get_progress_callback，在转发到 task_service 前记录 stage
        pipeline_progress_stages = []
        real_get_cb = DocumentProcessor.get_progress_callback

        def intercepted_get_progress_callback(self, task_id):
            real_cb = real_get_cb(self, task_id)

            async def recording_cb(stage, progress):
                pipeline_progress_stages.append(stage)
                await real_cb(stage, progress)

            return recording_cb

        l1_doc = _make_l1_doc()
        annotation = _make_annotation()

        processor = DocumentProcessor(mock_task_service, mock_storage, mock_gateway)

        with patch.object(DocumentProcessor, "get_progress_callback", intercepted_get_progress_callback), \
             patch.object(processor, "_download_pdf",
                          new_callable=AsyncMock, return_value=Path("/tmp/test.pdf")), \
             patch.object(pipeline_mod, "extract_l1_from_pdf", return_value=l1_doc), \
             patch.object(pipeline_mod, "build_ocr_chain", return_value=MagicMock(
                 extract=AsyncMock(return_value=MagicMock(pages=[])))), \
             patch.object(pipeline_mod, "extract_l1_from_ocr", return_value=l1_doc), \
             patch.object(pipeline_mod, "annotate_document",
                          new_callable=AsyncMock, return_value=annotation), \
             patch.object(pipeline_mod, "correct_anchors", return_value=annotation), \
             patch.object(pipeline_mod, "slice_questions", return_value=[]), \
             patch.object(pipeline_mod, "match_answers", return_value=[]), \
             patch.object(pipeline_mod, "evaluate_quality", return_value=[]):

            result = await processor.process_document(
                task_id=UUID("00000000-0000-0000-0000-000000000001"),
                document_id=UUID("00000000-0000-0000-0000-000000000002"),
                object_key="test.pdf",
                filename="test.pdf",
            )

        # 核心断言 1：真实 run_pipeline 发出了所有关键阶段
        assert "l1_generation" in pipeline_progress_stages, (
            f"l1_generation not in pipeline stages: {pipeline_progress_stages}"
        )
        assert "llm_annotation" in pipeline_progress_stages
        assert "anchor_correction" in pipeline_progress_stages
        assert "content_slicing" in pipeline_progress_stages
        assert "answer_matching" in pipeline_progress_stages
        assert "quality_gate" in pipeline_progress_stages
        assert "question_images" in pipeline_progress_stages

        # 核心断言 2：processor 正确转发了所有阶段到 task_service
        all_stages = [c["stage"] for c in progress_calls]
        assert "downloading" in all_stages or "downloaded" in all_stages
        assert "parsing" in all_stages
        for stage in pipeline_progress_stages:
            assert stage in all_stages, f"stage '{stage}' in pipeline but not in task_service calls"

        # 核心断言 3：task.current_stage 被更新到最后一个阶段
        task_id_str = "00000000-0000-0000-0000-000000000001"
        assert task_id_str in task_stages, "task current_stage was never set"
        assert task_stages[task_id_str] == "question_images"

        # progress 在 0-1 范围内
        for c in progress_calls:
            if c["progress"] is not None:
                assert 0 <= c["progress"] <= 1

        assert result.status == "succeeded"


class TestProcessorProgressCallbackForwarding:
    """验证 get_progress_callback() 正确转发到 task_service.update_progress。"""

    @pytest.mark.asyncio
    async def test_progress_callback_forwards_stage_and_progress(self):
        """get_progress_callback 返回的函数正确转发 stage 和 progress。"""
        from app.domains.document.processor import DocumentProcessor

        mock_task_service = AsyncMock()
        processor = DocumentProcessor(mock_task_service, MagicMock(), MagicMock())

        calls = []

        async def track(task_id, progress=None, stage=None):
            calls.append({"task_id": task_id, "progress": progress, "stage": stage})

        mock_task_service.update_progress = track

        task_id = UUID("00000000-0000-0000-0000-000000000001")
        cb = processor.get_progress_callback(task_id)

        await cb("l1_generation", 0.3)
        await cb("llm_annotation", 0.4)

        assert len(calls) == 2
        assert calls[0] == {"task_id": task_id, "progress": 0.3, "stage": "l1_generation"}
        assert calls[1] == {"task_id": task_id, "progress": 0.4, "stage": "llm_annotation"}

"""
Phase 2 CRITICAL 修复验证测试。

C5/C6: PipelineResult 三态 + processor 检查 result.status
C7: progress_callback 传入 run_pipeline
H1: L1 Postprocessor 保留 dual source 字段
C3: section 校验传播到 sq.issues
C4: 完形填空子题不要求 stem 重叠
H5: Worker 幂等 fail
"""
import pytest
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import UUID

from app.domains.document.pipeline_shared import PipelineResult
from app.domains.document.schemas_l1 import L1Document, L1Line, L1Page
from app.domains.document.schemas_l2 import (
    CorrectedAnchor,
    L2DocumentAnnotation,
    SlicedQuestion,
)


# ═══════════════════════════════════════════════════════════════════
# C5/C6: PipelineResult 三态
# ═══════════════════════════════════════════════════════════════════


class TestPipelineResultStatus:
    """C5/C6: PipelineResult 必须有 succeeded/failed/partial_failed 三态。"""

    def test_pipeline_result_has_status_field(self):
        """PipelineResult 默认 status 为 succeeded。"""
        r = PipelineResult()
        assert r.status == "succeeded"
        assert r.stage_errors == []

    def test_pipeline_result_to_dict_includes_status(self):
        """PipelineResult.to_dict() 包含 status 和 stage_errors。"""
        r = PipelineResult()
        d = r.to_dict()
        assert "status" in d
        assert d["status"] == "succeeded"
        assert "stage_errors" in d
        assert d["stage_errors"] == []

    def test_pipeline_result_failed_status(self):
        """PipelineResult 可以设置为 failed 并携带 stage_errors。"""
        r = PipelineResult()
        r.status = "failed"
        r.stage_errors.append({"stage": "llm_annotation", "error": "timeout"})
        d = r.to_dict()
        assert d["status"] == "failed"
        assert len(d["stage_errors"]) == 1
        assert d["stage_errors"][0]["stage"] == "llm_annotation"


# ═══════════════════════════════════════════════════════════════════
# C5/C6: processor 检查 result.status
# ═══════════════════════════════════════════════════════════════════


class TestProcessorChecksPipelineStatus:
    """C5/C6: processor 必须检查 result.status 决定任务状态。"""

    @pytest.mark.asyncio
    async def test_processor_fails_task_when_pipeline_status_failed(self):
        """Pipeline 返回 failed 时，processor 调用 fail_task 而非 succeed_task。"""
        from app.domains.document.processor import DocumentProcessor

        mock_task_service = AsyncMock()
        mock_task_service.commit = AsyncMock()
        mock_storage = MagicMock()
        mock_gateway = MagicMock()

        failed_result = PipelineResult()
        failed_result.status = "failed"
        failed_result.stage_errors = [{"stage": "llm_annotation", "error": "LLM timeout"}]
        failed_result.errors = ["Stage 3 (llm_annotation): LLM timeout"]

        processor = DocumentProcessor(mock_task_service, mock_storage, mock_gateway)

        with patch("app.domains.document.processor.run_simple_pipeline",
                   new_callable=AsyncMock, return_value=failed_result):
            with patch.object(processor, "_download_pdf",
                              new_callable=AsyncMock, return_value=Path("/tmp/test.pdf")):
                result = await processor.process_document(
                    task_id=UUID("00000000-0000-0000-0000-000000000001"),
                    document_id=UUID("00000000-0000-0000-0000-000000000002"),
                    object_key="test.pdf",
                    filename="test.pdf",
                )

        mock_task_service.fail_task.assert_called_once()
        mock_task_service.succeed_task.assert_not_called()
        assert result.status == "failed"

    @pytest.mark.asyncio
    async def test_processor_succeeds_task_when_pipeline_status_succeeded(self):
        """Pipeline 返回 succeeded 时，processor 调用 succeed_task。"""
        from app.domains.document.processor import DocumentProcessor

        mock_task_service = AsyncMock()
        mock_task_service.commit = AsyncMock()
        mock_storage = MagicMock()
        mock_gateway = MagicMock()

        success_result = PipelineResult()
        success_result.status = "succeeded"

        processor = DocumentProcessor(mock_task_service, mock_storage, mock_gateway)

        with patch("app.domains.document.processor.run_simple_pipeline",
                   new_callable=AsyncMock, return_value=success_result):
            with patch.object(processor, "_download_pdf",
                              new_callable=AsyncMock, return_value=Path("/tmp/test.pdf")):
                result = await processor.process_document(
                    task_id=UUID("00000000-0000-0000-0000-000000000001"),
                    document_id=UUID("00000000-0000-0000-0000-000000000002"),
                    object_key="test.pdf",
                    filename="test.pdf",
                )

        mock_task_service.succeed_task.assert_called_once()
        mock_task_service.fail_task.assert_not_called()
        assert result.status == "succeeded"


# ═══════════════════════════════════════════════════════════════════
# Fix 6/8: progress_callback 已移至 test_processor_progress.py
# ═══════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════
# H1: L1 Postprocessor 保留 dual source 字段
# ═══════════════════════════════════════════════════════════════════


class TestL1PostprocessorPreservesDualSourceFields:
    """H1: 拆行/重编号后必须保留 raw_sources/selected_source/evidence/confidence。"""

    def test_expand_question_number_preserves_fields(self):
        """题号拆行时保留 dual source 字段。"""
        from app.domains.document.l1_postprocessor import _expand_question_number_lines

        line = L1Line(
            line_id="P1L001", page_no=1, line_no_in_page=1, order=1,
            text="D. 既不充分也不必要条件5.已知...",
            block_type="text", source="ppsv3",
            raw_sources={"native": "D. 既不充分也不必要条件",
                         "ppsv3": "D. 既不充分也不必要条件5.已知..."},
            selected_source="native",
            evidence="bbox match",
            confidence=0.95,
        )

        result = _expand_question_number_lines([line])

        assert len(result) >= 2
        for r in result:
            assert r.raw_sources == line.raw_sources
            assert r.selected_source == "native"
            assert r.evidence == "bbox match"
            assert r.confidence == 0.95

    def test_renumber_lines_preserves_fields(self):
        """重编号时保留 dual source 字段。"""
        from app.domains.document.l1_postprocessor import _renumber_lines

        line = L1Line(
            line_id="P1L001", page_no=1, line_no_in_page=1, order=1,
            text="测试行", block_type="text", source="ppsv3",
            raw_sources={"native": "native text", "ppsv3": "ppsv3 text"},
            selected_source="ppsv3",
            evidence="ocr better",
            confidence=0.88,
        )

        result = _renumber_lines([line], "mixed")

        assert len(result) == 1
        r = result[0]
        assert r.raw_sources == {"native": "native text", "ppsv3": "ppsv3 text"}
        assert r.selected_source == "ppsv3"
        assert r.evidence == "ocr better"
        assert r.confidence == 0.88

    def test_inline_option_split_preserves_fields(self):
        """选项拆行时保留 dual source 字段。"""
        from app.domains.document.l1_postprocessor import _expand_inline_option_lines

        line = L1Line(
            line_id="P1L001", page_no=1, line_no_in_page=1, order=1,
            text="A.充分不必要条件 B.必要不充分条件 C.充要条件 D.既不充分也不必要条件",
            block_type="text", source="ppsv3",
            raw_sources={"native": "A.充分不必要条件",
                         "ppsv3": "A.充分不必要条件 B.必要不充分条件"},
            selected_source="native",
            evidence="better layout",
            confidence=0.92,
        )

        result = _expand_inline_option_lines([line])

        assert len(result) == 4
        for r in result:
            assert r.raw_sources == line.raw_sources
            assert r.selected_source == "native"
            assert r.evidence == "better layout"
            assert r.confidence == 0.92


# ═══════════════════════════════════════════════════════════════════
# C3: Section validation propagates to sq.issues
# ═══════════════════════════════════════════════════════════════════


class TestSectionValidationIsTrustedToLlm:
    """C3: section 类型与题组边界信任 LLM，不再写入规则告警。"""

    def test_section_validation_does_not_write_issues(self):
        """题号不连续不再写入 sq.issues。"""
        from app.domains.document.content_slicer import _validate_shared_material_sections

        sq1 = SlicedQuestion(
            question_number="1", question_type="single_choice",
            section_id="reading_1",
            stem_anchor=CorrectedAnchor(
                field="stem", llm_line_ids=["P1L003"],
                corrected_line_ids=["P1L003"], anchor_status="exact",
            ),
        )
        sq2 = SlicedQuestion(
            question_number="3", question_type="single_choice",
            section_id="reading_1",
            stem_anchor=CorrectedAnchor(
                field="stem", llm_line_ids=["P1L010"],
                corrected_line_ids=["P1L010"], anchor_status="exact",
            ),
        )

        _validate_shared_material_sections([sq1, sq2])

        assert not any("题号不连续" in i for i in sq1.issues)
        assert not any("题号不连续" in i for i in sq2.issues)

    def test_section_validation_single_question_not_flagged(self):
        """单题 section 不再标记为潜在问题。"""
        from app.domains.document.content_slicer import _validate_shared_material_sections

        sq = SlicedQuestion(
            question_number="1", question_type="single_choice",
            section_id="reading_1",
        )

        _validate_shared_material_sections([sq])

        assert not any("仅包含单题" in i for i in sq.issues)

    def test_ordinary_single_question_section_not_flagged(self):
        """普通独立题/大题 section 的单题不标记为 section 不完整。"""
        from app.domains.document.content_slicer import _validate_shared_material_sections

        sq = SlicedQuestion(
            question_number="31", question_type="short_answer",
            section_id="31_边疆治理",
        )

        _validate_shared_material_sections([sq])

        assert not any("仅包含单题" in i for i in sq.issues)

    def test_ordinary_section_question_gap_not_flagged(self):
        """普通大题 section 的题号间隔由题号全集校验兜底，不重复扣分。"""
        from app.domains.document.content_slicer import _validate_shared_material_sections

        sq1 = SlicedQuestion(
            question_number="11", question_type="single_choice",
            section_id="第一部分_选择题",
        )
        sq2 = SlicedQuestion(
            question_number="14", question_type="single_choice",
            section_id="第一部分_选择题",
        )

        _validate_shared_material_sections([sq1, sq2])

        assert not any("题号不连续" in i for i in sq1.issues)
        assert not any("题号不连续" in i for i in sq2.issues)


# ═══════════════════════════════════════════════════════════════════
# C4: 完形填空子题不要求 stem 重叠
# ═══════════════════════════════════════════════════════════════════


class TestProcessorPartialFailedDoesNotSucceed:
    """Fix 4: processor 必须对 partial_failed 调用 fail_task，不调用 succeed_task。"""

    @pytest.mark.asyncio
    async def test_processor_partial_failed_does_not_succeed_task(self):
        """Pipeline 返回 partial_failed → processor 调用 fail_task。"""
        from app.domains.document.processor import DocumentProcessor

        mock_task_service = AsyncMock()
        mock_task_service.commit = AsyncMock()
        mock_storage = MagicMock()
        mock_gateway = MagicMock()

        partial_result = PipelineResult()
        partial_result.status = "partial_failed"
        partial_result.errors = ["partial error"]

        processor = DocumentProcessor(mock_task_service, mock_storage, mock_gateway)

        with patch("app.domains.document.processor.run_simple_pipeline",
                   new_callable=AsyncMock, return_value=partial_result):
            with patch.object(processor, "_download_pdf",
                              new_callable=AsyncMock, return_value=Path("/tmp/test.pdf")):
                result = await processor.process_document(
                    task_id=UUID("00000000-0000-0000-0000-000000000001"),
                    document_id=UUID("00000000-0000-0000-0000-000000000002"),
                    object_key="test.pdf",
                    filename="test.pdf",
                )

        mock_task_service.fail_task.assert_called_once()
        mock_task_service.succeed_task.assert_not_called()
        assert result.status == "partial_failed"
    """C4: 完形填空子题不要求 stem_line_ids 重叠。"""

    def test_cloze_no_common_stem_not_flagged(self):
        """完形填空子题无共同 stem 行时不报错。"""
        from app.domains.document.content_slicer import _validate_shared_material_sections

        sq1 = SlicedQuestion(
            question_number="1", question_type="fill_in",
            section_id="cloze_1",
            stem_anchor=CorrectedAnchor(
                field="stem", llm_line_ids=["P1L003"],
                corrected_line_ids=["P1L003"], anchor_status="exact",
            ),
        )
        sq2 = SlicedQuestion(
            question_number="2", question_type="fill_in",
            section_id="cloze_1",
            stem_anchor=CorrectedAnchor(
                field="stem", llm_line_ids=["P1L008"],
                corrected_line_ids=["P1L008"], anchor_status="exact",
            ),
        )

        _validate_shared_material_sections([sq1, sq2])

        assert not any("无共同 stem 行" in i for i in sq1.issues)
        assert not any("无共同 stem 行" in i for i in sq2.issues)

    def test_non_cloze_no_common_stem_not_flagged(self):
        """section 边界信任 LLM，非完形无共同 stem 行不再报错。"""
        from app.domains.document.content_slicer import _validate_shared_material_sections

        sq1 = SlicedQuestion(
            question_number="1", question_type="single_choice",
            section_id="reading_1",
            stem_anchor=CorrectedAnchor(
                field="stem", llm_line_ids=["P1L003"],
                corrected_line_ids=["P1L003"], anchor_status="exact",
            ),
        )
        sq2 = SlicedQuestion(
            question_number="2", question_type="single_choice",
            section_id="reading_1",
            stem_anchor=CorrectedAnchor(
                field="stem", llm_line_ids=["P1L010"],
                corrected_line_ids=["P1L010"], anchor_status="exact",
            ),
        )

        _validate_shared_material_sections([sq1, sq2])

        assert not any("shared_material_line_ids" in i or "缺少" in i for i in sq1.issues)
        assert not any("shared_material_line_ids" in i or "缺少" in i for i in sq2.issues)


# ═══════════════════════════════════════════════════════════════════
# H5: Worker 幂等 fail（不 double-fail）
# ═══════════════════════════════════════════════════════════════════


class TestWorkerNoDoubleFail:
    """H5: Worker 不应对已失败的任务重复 fail。"""

    @pytest.mark.asyncio
    async def test_worker_inner_handler_does_not_double_fail(self):
        """Processor 已 fail_task 后，Worker 内层 except 不再重复 fail。

        验证：processor.process_document 抛异常时，worker 内层 except
        只更新 document 状态，不调用 task_service.fail_task（因为 processor 内部已处理）。
        """
        from app.worker.document_worker import document_parse_worker

        mock_session = AsyncMock()
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
        mock_task_service.get_task = AsyncMock(
            return_value=MagicMock(status="failed")
        )
        mock_doc_service.get_document = AsyncMock(return_value=mock_doc)

        mock_storage = MagicMock()
        mock_gateway = MagicMock()

        with patch("app.domains.document.processor.DocumentProcessor") as MockProcessor:
            mock_instance = AsyncMock()
            mock_instance.process_document = AsyncMock(
                side_effect=RuntimeError("pipeline error")
            )
            MockProcessor.return_value = mock_instance

            worker_task = asyncio.create_task(
                document_parse_worker(
                    storage=mock_storage,
                    gateway=mock_gateway,
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

        # processor 抛异常后，worker 内层只更新 document 状态
        # 不应调用 task_service.fail_task（processor 内部已处理）
        mock_task_service.fail_task.assert_not_called()
        # document 状态应被更新为 failed
        assert mock_doc.processing_status == "failed"


# ═══════════════════════════════════════════════════════════════════
# 独立单选题不被 section 校验标记
# ═══════════════════════════════════════════════════════════════════


class TestMathIndependentSingleChoiceNotFlagged:
    """独立单选题不应被 section 校验标记。"""

    def test_independent_single_choice_no_issues(self):
        """无 section_id 的单选题不产生 section 校验 issues。"""
        from app.domains.document.content_slicer import _validate_shared_material_sections

        sq = SlicedQuestion(
            question_number="1", question_type="single_choice",
            stem_anchor=CorrectedAnchor(
                field="stem", llm_line_ids=["P1L003"],
                corrected_line_ids=["P1L003"], anchor_status="exact",
            ),
        )

        _validate_shared_material_sections([sq])

        assert sq.issues == []

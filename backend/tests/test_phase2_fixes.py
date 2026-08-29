"""
Phase 2 增量修复测试（Task 2.2 / 2.4）。

Task 2.2: _build_question_images 使用 L1 真实 bbox + per-image fallback
Task 2.4: Worker 端到端测试
"""
import pytest
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

from app.domains.document.pipeline_shared import _build_question_images
from app.domains.document.pipeline import _merge_dual_source
from app.domains.document.schemas_l1 import L1Document, L1Line, L1Page, L1Image


def _make_line(line_id: str, text: str, bbox: dict | None = None, page_no: int = 1) -> L1Line:
    return L1Line(
        line_id=line_id,
        page_no=page_no,
        line_no_in_page=1,
        order=1,
        text=text,
        block_type="text",
        bbox=bbox or {"x1": 100, "y1": 200, "x2": 400, "y2": 220},
    )


def _make_image(image_id: str, bbox: dict, page_no: int = 1, placement: str = "stem") -> L1Image:
    return L1Image(
        image_id=image_id,
        page_no=page_no,
        bbox=bbox,
        source="ppsv3",
        placement=placement,
    )


def _make_doc(
    lines: list[L1Line],
    images: list[L1Image] | None = None,
) -> L1Document:
    return L1Document(
        filename="test.pdf",
        pages=[
            L1Page(page_no=1, lines=lines),
            L1Page(page_no=2, lines=[]),
        ],
        lines=lines,
        images=images or [],
        total_pages=2,
    )


class TestBuildQuestionImagesWithL1Bbox:
    """Task 2.2: _build_question_images 使用 L1 真实 bbox。"""

    def test_image_inside_line_bbox_is_associated(self):
        """图片 bbox 在 L1 行 bbox 范围内时关联到该题。"""
        line1 = _make_line("P1L001", "1. 三角形面积公式：",
                           bbox={"x1": 100, "y1": 200, "x2": 500, "y2": 220})
        line2 = _make_line("P1L002", "A. S=ah/2",
                           bbox={"x1": 100, "y1": 220, "x2": 300, "y2": 240})
        # 图片在 line1 范围内
        image1 = _make_image("img1", bbox={"x1": 200, "y1": 210, "x2": 400, "y2": 250})

        doc = _make_doc([line1, line2], [image1])

        q1 = MagicMock()
        q1.source_page = 1
        q1.stem_line_ids = ["P1L001"]
        q1.options_line_ids = ["P1L002"]
        q1.question_number = "1"

        result = _build_question_images([q1], doc.images, doc)

        assert result == [{
            "question_number": "1", "sub_question_qno": None, "image_id": "img1", "placement": "stem",
            "page_no": 1,
            "bbox": {"x1": 200, "y1": 210, "x2": 400, "y2": 250},
            "source": "ppsv3", "figure_id": "",
            "url": None,  # 2026-08-27：_build_question_images 携带 img.url（v6.41）
        }]

    def test_image_outside_all_lines_not_associated(self):
        """图片 bbox 不在任何题目的 L1 行范围内时不关联。"""
        line1 = _make_line("P1L001", "1. 三角形面积公式：",
                           bbox={"x1": 100, "y1": 200, "x2": 500, "y2": 220})
        # 图片在完全不同的区域
        image1 = _make_image("img1", bbox={"x1": 600, "y1": 800, "x2": 800, "y2": 820})

        doc = _make_doc([line1], [image1])

        q1 = MagicMock()
        q1.source_page = 1
        q1.stem_line_ids = ["P1L001"]
        q1.options_line_ids = []
        q1.question_number = "1"

        result = _build_question_images([q1], doc.images, doc)

        assert result == []

    def test_image_near_line_border_is_associated(self):
        """图片与 L1 行 bbox 相邻（20px 模糊区域）时仍关联。"""
        line1 = _make_line("P1L001", "1. 三角形面积公式：",
                           bbox={"x1": 100, "y1": 200, "x2": 500, "y2": 220})
        # 图片紧邻 line1 底部（15px 内，在 20px margin 内）
        image1 = _make_image("img1", bbox={"x1": 200, "y1": 230, "x2": 400, "y2": 250})

        doc = _make_doc([line1], [image1])

        q1 = MagicMock()
        q1.source_page = 1
        q1.stem_line_ids = ["P1L001"]
        q1.options_line_ids = []
        q1.question_number = "1"

        result = _build_question_images([q1], doc.images, doc)

        assert result == [{
            "question_number": "1", "sub_question_qno": None, "image_id": "img1", "placement": "stem",
            "page_no": 1,
            "bbox": {"x1": 200, "y1": 230, "x2": 400, "y2": 250},
            "source": "ppsv3", "figure_id": "",
            "url": None,  # 2026-08-27：_build_question_images 携带 img.url（v6.41）
        }]

    def test_no_bbox_image_not_associated(self):
        """无 bbox 图片不关联（禁止无证据广播，V1_LESSONS 3.26）。"""
        # 图片无 bbox：不能关联（旧行为"广播到第一题"违反无证据广播抑制）
        image1 = L1Image(image_id="img1", page_no=1, source="ppsv3", placement="stem")

        q1 = MagicMock()
        q1.source_page = 1
        q1.question_number = "1"

        result = _build_question_images([q1], [image1], None)

        assert result == []

    def test_standalone_image_not_associated(self):
        """placement=standalone 的图片不关联。"""
        line1 = _make_line("P1L001", "1. 三角形面积公式：",
                           bbox={"x1": 100, "y1": 200, "x2": 500, "y2": 220})
        image1 = _make_image("img1", bbox={"x1": 200, "y1": 210, "x2": 400, "y2": 250},
                             placement="standalone")

        doc = _make_doc([line1], [image1])

        q1 = MagicMock()
        q1.source_page = 1
        q1.stem_line_ids = ["P1L001"]
        q1.options_line_ids = []
        q1.question_number = "1"

        result = _build_question_images([q1], doc.images, doc)

        assert result == []

    def test_answer_area_image_on_answer_page_is_associated(self):
        """答案/详解区的图片应通过 answer_line_ids 关联到题，placement=answer_area。"""
        line5 = L1Line(
            line_id="P5L001",
            page_no=5,
            line_no_in_page=1,
            order=1,
            text="解：...",
            block_type="text",
            bbox={"x1": 100, "y1": 800, "x2": 500, "y2": 900},
        )
        image = L1Image(
            image_id="P5IMG001",
            page_no=5,
            bbox={"x1": 200, "y1": 810, "x2": 400, "y2": 880},
            source="ppsv3",
            placement="unknown",
        )
        doc = L1Document(
            filename="test.pdf",
            pages=[L1Page(page_no=5, lines=[line5])],
            lines=[line5],
            images=[image],
            total_pages=5,
        )

        q1 = MagicMock()
        q1.source_page = 2
        q1.stem_line_ids = []
        q1.options_line_ids = []
        q1.answer_line_ids = ["P5L001"]
        q1.question_number = "17"

        result = _build_question_images([q1], doc.images, doc)

        assert result == [
            {
                "question_number": "17",
                "sub_question_qno": None,
                "image_id": "P5IMG001",
                "placement": "answer_area",
                "page_no": 5,
                "bbox": {"x1": 200, "y1": 810, "x2": 400, "y2": 880},
                "source": "ppsv3",
                "figure_id": "",
                "url": None,  # 2026-08-27：_build_question_images 携带 img.url（v6.41）
            }
        ]


class TestMergeDualSourceImageFallback:
    """Task 2.2: per-image fallback 和 missing_figure 测试。"""

    def test_native_image_without_bbox_not_added(self):
        """无 bbox 的 native 图片不添加到结果（V1_LESSONS 3.4: 不整页兜底）。"""
        native_line = _make_line("P1L001", "1. 题目",
                                 bbox={"x1": 100, "y1": 200, "x2": 500, "y2": 220})
        native_doc = L1Document(
            filename="native.pdf",
            pages=[L1Page(page_no=1, lines=[native_line])],
            lines=[native_line],
            images=[L1Image(image_id="nat1", page_no=1, source="native")],  # 无 bbox
            total_pages=1,
        )

        ppsv3_line = _make_line("P1L001", "1. 题目",
                                bbox={"x1": 200, "y1": 400, "x2": 1000, "y2": 440})
        ppsv3_doc = L1Document(
            filename="ppsv3.pdf",
            pages=[L1Page(page_no=1, lines=[ppsv3_line])],
            lines=[ppsv3_line],
            images=[],
            total_pages=1,
        )

        result_doc, _ = _merge_dual_source(native_doc, ppsv3_doc)

        # 无 bbox 的 native 图片不应添加到结果
        assert len(result_doc.images) == 0

    def test_native_image_with_same_position_as_ppsv3_not_duplicated(self):
        """与 ppsv3 图片位置相同的 native 图片不应重复添加。"""
        native_line = _make_line("P1L001", "1. 题目",
                                 bbox={"x1": 100, "y1": 200, "x2": 500, "y2": 220})
        native_doc = L1Document(
            filename="native.pdf",
            pages=[L1Page(page_no=1, lines=[native_line])],
            lines=[native_line],
            images=[L1Image(image_id="nat1", page_no=1, source="native",
                            bbox={"x1": 100, "y1": 200, "x2": 300, "y2": 240})],
            total_pages=1,
        )

        ppsv3_line = _make_line("P1L001", "1. 题目",
                                bbox={"x1": 200, "y1": 400, "x2": 1000, "y2": 440})
        ppsv3_doc = L1Document(
            filename="ppsv3.pdf",
            pages=[L1Page(page_no=1, lines=[ppsv3_line])],
            lines=[ppsv3_line],
            # ppsv3 图片在相同位置（缩放后）
            images=[L1Image(image_id="pp1", page_no=1, source="ppsv3",
                            bbox={"x1": 200, "y1": 400, "x2": 600, "y2": 480})],
            total_pages=1,
        )

        result_doc, _ = _merge_dual_source(native_doc, ppsv3_doc)

        # native 图片与 ppsv3 位置相同，不应重复添加
        assert len(result_doc.images) == 1
        assert result_doc.images[0].image_id == "pp1"

    def test_native_image_without_ppsv3_match_added(self):
        """无 ppsv3 对应的 native 图片应补充添加。"""
        native_line = _make_line("P1L001", "1. 题目",
                                 bbox={"x1": 100, "y1": 200, "x2": 500, "y2": 220})
        native_doc = L1Document(
            filename="native.pdf",
            pages=[L1Page(page_no=1, lines=[native_line])],
            lines=[native_line],
            images=[L1Image(image_id="nat1", page_no=1, source="native",
                            bbox={"x1": 100, "y1": 200, "x2": 300, "y2": 240})],
            total_pages=1,
        )

        ppsv3_line = _make_line("P1L001", "1. 题目",
                                bbox={"x1": 200, "y1": 400, "x2": 1000, "y2": 440})
        ppsv3_doc = L1Document(
            filename="ppsv3.pdf",
            pages=[L1Page(page_no=1, lines=[ppsv3_line])],
            lines=[ppsv3_line],
            images=[],  # ppsv3 无图片
            total_pages=1,
        )

        result_doc, _ = _merge_dual_source(native_doc, ppsv3_doc)

        # native 图片无 ppsv3 对应，应补充添加
        assert len(result_doc.images) == 1
        assert result_doc.images[0].image_id == "nat1"
    """Task 2.4: Worker 端到端测试。"""

    @pytest.mark.asyncio
    async def test_worker_polls_and_processes_task(self):
        """Worker 轮询到 queued 任务后调用回调。"""
        from app.worker.document_worker import document_parse_worker

        mock_callback = AsyncMock()
        mock_session = AsyncMock()
        mock_session.close = AsyncMock()
        mock_task_service = MagicMock()
        mock_doc_service = MagicMock()
        mock_callback.return_value = (mock_session, mock_task_service, mock_doc_service)

        mock_task = MagicMock()
        mock_task.id = "task-1"
        mock_task.type = "document_parse"
        mock_task.status = "queued"
        mock_task.document_id = "doc-1"
        mock_task.callback_method = "doc_parse"

        mock_doc = MagicMock()
        mock_doc.id = "doc-1"
        mock_doc.processing_status = "pending"

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.side_effect = [mock_task, mock_doc, None]
        mock_session.execute = AsyncMock(return_value=mock_result)

        stop_event = asyncio.Event()
        call_count = 0

        async def counting_callback():
            nonlocal call_count
            call_count += 1
            if call_count >= 1:
                stop_event.set()
            return mock_session, mock_task_service, mock_doc_service

        mock_storage = MagicMock()
        mock_gateway = MagicMock()

        worker_task = asyncio.create_task(
            document_parse_worker(
                storage=mock_storage,
                gateway=mock_gateway,
                create_task_services=counting_callback,
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

        assert call_count >= 1

    @pytest.mark.asyncio
    async def test_worker_handles_callback_exception(self):
        """Worker 处理任务失败时不崩溃。"""
        from app.worker.document_worker import document_parse_worker

        call_count = 0
        stop_event = asyncio.Event()

        async def failing_callback():
            nonlocal call_count
            call_count += 1
            if call_count >= 1:
                stop_event.set()
            raise RuntimeError("PDF parse failed")

        mock_storage = MagicMock()
        mock_gateway = MagicMock()

        worker_task = asyncio.create_task(
            document_parse_worker(
                storage=mock_storage,
                gateway=mock_gateway,
                create_task_services=failing_callback,
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

        assert call_count >= 1

"""
Fix 1 (CRITICAL): Pipeline 双源 L1 空结果必须失败。

空 L1Document 归一化为 None，避免空结果通过 merge 后仍 succeeded。
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.domains.document.schemas_l1 import L1Document, L1Line, L1Page


def _make_native_doc() -> L1Document:
    """构造有内容的 native L1 文档。"""
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


def _make_ppsv3_doc() -> L1Document:
    """构造有内容的 ppsv3 L1 文档。"""
    lines = [
        L1Line("P1L001", 1, 1, 1, "1. 测试题干", "text", source="ppsv3"),
        L1Line("P1L002", 1, 2, 2, "（A）选项A", "text", source="ppsv3"),
        L1Line("P1L003", 1, 3, 3, "（B）选项B", "text", source="ppsv3"),
    ]
    return L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source="ppsv3",
        total_pages=1,
    )


def _make_empty_doc() -> L1Document:
    """构造空 L1 文档（lines=[]）。"""
    return L1Document(
        filename="test.pdf",
        pages=[],
        lines=[],
        source="ppsv3",
        total_pages=1,
    )


class TestPipelineEmptySourcesFail:
    """Fix 1 (CRITICAL): 双源为空时 pipeline 必须 failed。"""

    def test_pipeline_l1_empty_sources_fail(self):
        """两个空 L1Document → result.status == 'failed'。"""
        from app.domains.document.pipeline import run_pipeline

        mock_gateway = AsyncMock()

        empty_native = _make_empty_doc()
        empty_ppsv3 = _make_empty_doc()

        result = asyncio.run(run_pipeline(
            native_doc=empty_native,
            ppsv3_doc=empty_ppsv3,
            gateway=mock_gateway,
        ))

        assert result.status == "failed"
        assert len(result.stage_errors) == 1
        assert result.stage_errors[0]["stage"] == "l1_generation"


class TestPipelineEmptyPpsv3UsesNative:
    """Fix 1 (CRITICAL): ppsv3 为空时归一化为 None，走仅 native 路径。"""

    def test_pipeline_l1_empty_ppsv3_uses_native(self):
        """native 有内容、ppsv3 空 → 归一化后走仅 native 路径 → succeeded。"""
        from app.domains.document.pipeline import run_pipeline
        from app.domains.document.schemas_l2 import L2DocumentAnnotation

        mock_gateway = AsyncMock()
        native_doc = _make_native_doc()
        empty_ppsv3 = _make_empty_doc()

        with patch("app.domains.document.pipeline.annotate_document",
                   new_callable=AsyncMock) as mock_annotate:
            mock_annotate.return_value = L2DocumentAnnotation(filename="test.pdf")
            result = asyncio.run(run_pipeline(
                native_doc=native_doc,
                ppsv3_doc=empty_ppsv3,
                gateway=mock_gateway,
            ))

        assert result.status == "succeeded"
        assert result.l1_document is not None
        assert result.l1_document.source == "native"
        assert result.errors == []


class TestPipelineEmptyNativeUsesPpsv3:
    """Fix 1 (CRITICAL): native 为空时归一化为 None，走仅 ppsv3 路径。"""

    def test_pipeline_l1_empty_native_uses_ppsv3(self):
        """ppsv3 有内容、native 空 → 归一化后走仅 ppsv3 路径 → succeeded。"""
        from app.domains.document.pipeline import run_pipeline
        from app.domains.document.schemas_l2 import L2DocumentAnnotation

        mock_gateway = AsyncMock()
        empty_native = _make_empty_doc()
        ppsv3_doc = _make_ppsv3_doc()

        with patch("app.domains.document.pipeline.annotate_document",
                   new_callable=AsyncMock) as mock_annotate:
            mock_annotate.return_value = L2DocumentAnnotation(filename="test.pdf")
            result = asyncio.run(run_pipeline(
                native_doc=empty_native,
                ppsv3_doc=ppsv3_doc,
                gateway=mock_gateway,
            ))

        assert result.status == "succeeded"
        assert result.l1_document is not None
        assert result.l1_document.source == "ppsv3"
        assert result.errors == []

"""Prompt A/B 切换测试。

验证 use_modular_prompt 参数能正确透传到 build_annotation_prompt，
并且 modular 和 legacy Prompt 内容不同。
"""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from app.domains.document.line_annotator import (
    build_annotation_prompt,
    annotate_document,
    ANNOTATION_PROMPT_VERSION,
    LEGACY_ANNOTATION_PROMPT_VERSION,
)
from app.domains.document.schemas_l1 import L1Document, L1Line


def _make_simple_doc() -> L1Document:
    """创建简单的测试文档。"""
    lines = [
        L1Line(line_id="P1L001", text="1. What is 1+1?", page_no=1, line_no_in_page=1, order=1, block_type="text"),
        L1Line(line_id="P1L002", text="A. 1  B. 2  C. 3  D. 4", page_no=1, line_no_in_page=2, order=2, block_type="text"),
    ]
    return L1Document(
        filename="test.pdf",
        lines=lines,
    )


class TestBuildAnnotationPromptLegacyFallback:
    """测试 build_annotation_prompt 的 legacy fallback。"""

    def test_legacy_prompt_does_not_contain_subject_rules(self):
        """旧 Prompt 不包含科目专用规则。"""
        doc = _make_simple_doc()
        legacy = build_annotation_prompt(doc, use_modular_prompt=False, subject="英语")
        modular = build_annotation_prompt(doc, use_modular_prompt=True, subject="英语")

        # legacy 不包含科目专用规则
        assert "## 数学专用规则" not in legacy
        assert "## 英语专用规则" not in legacy

        # modular 包含科目专用规则
        assert "## 英语专用规则" in modular

    def test_legacy_and_modular_are_different(self):
        """旧 Prompt 和模块化 Prompt 内容不同。"""
        doc = _make_simple_doc()
        legacy = build_annotation_prompt(doc, use_modular_prompt=False)
        modular = build_annotation_prompt(doc, use_modular_prompt=True)

        assert legacy != modular

    def test_legacy_contains_old_prompt_content(self):
        """旧 Prompt 包含旧版内容。"""
        doc = _make_simple_doc()
        legacy = build_annotation_prompt(doc, use_modular_prompt=False)

        # 旧 Prompt 包含特定关键词
        assert "综合题识别（材料题必须合并）" in legacy


class TestAnnotateDocumentForwardsFlag:
    """测试 annotate_document 透传 use_modular_prompt 参数。"""

    def test_annotate_document_sets_modular_version(self):
        """使用模块化 Prompt 时，annotation_version 为 modular 版本。"""
        doc = _make_simple_doc()
        gateway = MagicMock()
        gateway.complete = AsyncMock(return_value='{"questions": []}')

        result = asyncio.run(annotate_document(doc, gateway, use_modular_prompt=True))
        assert result.annotation_version == ANNOTATION_PROMPT_VERSION

    def test_annotate_document_sets_legacy_version(self):
        """使用旧 Prompt 时，annotation_version 为 legacy 版本。"""
        doc = _make_simple_doc()
        gateway = MagicMock()
        gateway.complete = AsyncMock(return_value='{"questions": []}')

        result = asyncio.run(annotate_document(doc, gateway, use_modular_prompt=False))
        assert result.annotation_version == LEGACY_ANNOTATION_PROMPT_VERSION


class TestPromptVersionConstants:
    """测试 Prompt 版本常量。"""

    def test_versions_are_different(self):
        """modular 和 legacy 版本号不同。"""
        assert ANNOTATION_PROMPT_VERSION != LEGACY_ANNOTATION_PROMPT_VERSION

    def test_modular_version_format(self):
        """modular 版本号格式正确。"""
        assert "modular" in ANNOTATION_PROMPT_VERSION

    def test_legacy_version_format(self):
        """legacy 版本号格式正确。"""
        assert "legacy" in LEGACY_ANNOTATION_PROMPT_VERSION

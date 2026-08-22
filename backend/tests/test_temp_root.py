"""Guard against sandbox temp regressions."""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock


def test_tempfile_uses_workspace_root() -> None:
    """tempfile.tempdir 必须是工作区可管理的目录（含 aitutor_pytest 后缀）。"""
    tmp = Path(tempfile.gettempdir())
    assert tmp.name == "aitutor_pytest", f"tempdir 应含 aitutor_pytest 后缀，实际 {tmp}"
    assert tmp.is_dir(), f"tempdir 不存在: {tmp}"

    fd, name = tempfile.mkstemp()
    os.close(fd)
    try:
        assert Path(name).is_relative_to(tmp)
    finally:
        Path(name).unlink(missing_ok=True)


def test_pytest_tmp_path_uses_workspace_root(tmp_path: Path) -> None:
    """pytest tmp_path 应在 tempfile 管理的 tempdir 下。"""
    tmp = Path(tempfile.gettempdir())
    assert tmp_path.is_relative_to(tmp)


def test_processor_download_uses_workspace_tmp() -> None:
    from app.domains.document.processor import DocumentProcessor, _WORKSPACE_TMP

    storage = MagicMock()
    storage.get_object.return_value = b"%PDF-1.4 fake"
    processor = DocumentProcessor(
        task_service=MagicMock(),
        storage=storage,
        gateway=MagicMock(),
    )

    pdf_path = asyncio.run(processor._download_pdf("object-key", "sample.pdf"))
    assert pdf_path.parent.is_relative_to(_WORKSPACE_TMP)

    pdf_path.unlink(missing_ok=True)
    pdf_path.parent.rmdir()

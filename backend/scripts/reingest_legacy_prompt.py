"""Legacy Prompt 重入库脚本。

用旧 Prompt 重新处理东城英语文档，入库后通过 annotation_version 区分数据。

用法：
    python -X utf8 scripts/reingest_legacy_prompt.py
"""

import asyncio
import json
import sys
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.database import engine
from app.domains.document.simple_pipeline import run_simple_pipeline
from app.domains.document.line_annotator import LEGACY_ANNOTATION_PROMPT_VERSION
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_document_info():
    """获取东城英语文档信息。"""
    async with AsyncSession(engine) as session:
        result = await session.execute(text("""
            SELECT id::text, filename, object_key, subject
            FROM documents
            WHERE filename LIKE '%东城%'
            ORDER BY created_at DESC
            LIMIT 1
        """))
        row = result.mappings().first()
        if not row:
            raise RuntimeError("东城英语文档未找到")
        return {
            "id": row["id"],
            "filename": row["filename"],
            "object_key": row["object_key"],
            "subject": row["subject"],
        }


async def get_pdf_path(object_key: str) -> Path:
    """从 object_key 获取 PDF 路径（本地部署场景直接用文件系统）。"""
    # 本地部署：object_key 就是文件路径
    pdf_path = Path(object_key)
    if not pdf_path.exists():
        # 尝试在 uploads 目录查找
        uploads_dir = ROOT / "uploads"
        pdf_path = uploads_dir / object_key
    if not pdf_path.exists():
        # 尝试在 test/pdf 目录查找
        test_pdf_dir = ROOT.parent / "test" / "pdf"
        # 从 object_key 提取文件名
        filename = Path(object_key).name
        pdf_path = test_pdf_dir / filename
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF 文件不存在: {object_key}")
    return pdf_path


async def run_legacy_reingestion():
    """运行 legacy Prompt 重入库。"""
    print("=" * 70)
    print("Legacy Prompt Re-ingestion")
    print("=" * 70)
    print()

    # 1. 获取文档信息
    doc_info = await get_document_info()
    print(f"Document: {doc_info['filename']}")
    print(f"Subject: {doc_info['subject']}")
    print()

    # 2. 获取 PDF 路径
    pdf_path = await get_pdf_path(doc_info["object_key"])
    print(f"PDF path: {pdf_path}")
    print()

    # 3. 获取 LLM gateway
    from app.ai.gateway import get_llm_gateway
    gateway = get_llm_gateway()
    print(f"LLM gateway mode: {gateway.mode}")
    print()

    # 4. 运行 legacy pipeline
    print(f"Running legacy prompt ({LEGACY_ANNOTATION_PROMPT_VERSION})...")
    print("-" * 70)

    result = await run_simple_pipeline(
        pdf_path=pdf_path,
        filename=doc_info["filename"],
        subject=doc_info["subject"],
        gateway=gateway,
        use_modular_prompt=False,
    )

    print(f"Pipeline status: {result.status}")
    print(f"Questions: {len(result.l2_annotation.questions) if result.l2_annotation else 0}")
    print()

    if result.status == "failed":
        print(f"Errors: {result.errors}")
        return

    # 5. 保存 L2 结果到 document 表
    if result.l2_annotation:
        from app.worker.document_worker import _serialize_l2_for_persistence
        annotated_data = _serialize_l2_for_persistence(result.l2_annotation)
        llm_annotated = json.dumps(annotated_data, ensure_ascii=False, indent=2)

        async with AsyncSession(engine) as session:
            await session.execute(text("""
                UPDATE documents
                SET llm_annotated_markdown = :data
                WHERE id::text = :doc_id
            """), {"data": llm_annotated, "doc_id": doc_info["id"]})
            await session.commit()
            print(f"Saved L2 annotation to document {doc_info['id'][:8]}...")

    # 6. 验证版本标记
    async with AsyncSession(engine) as session:
        result = await session.execute(text("""
            SELECT llm_annotated_markdown::text
            FROM documents
            WHERE id::text = :doc_id
        """), {"doc_id": doc_info["id"]})
        row = result.mappings().first()
        if row and row['llm_annotated_markdown']:
            data = json.loads(row['llm_annotated_markdown'])
            version = data.get("annotation_version", "N/A")
            print(f"Annotation version in DB: {version}")
            print(f"Expected: {LEGACY_ANNOTATION_PROMPT_VERSION}")
            print(f"Match: {version == LEGACY_ANNOTATION_PROMPT_VERSION}")

    print()
    print("=" * 70)
    print("Legacy 重入库完成。")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_legacy_reingestion())

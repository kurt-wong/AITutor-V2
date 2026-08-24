"""回填语文题 stem 的共享材料（2026-08-25）。

背景：语文重跑（task fcf94f72）用旧 content_slicer（P0-5：独立题剔除材料），
LLM 将材料阅读/文言文题标为独立题但提供 shared_material_line_ids，
材料未进 stem → 题目失去材料上下文（报告材料覆盖 0%）。

content_slicer 已修复（独立题带共享材料也并入 stem，材料在前去重），
本脚本用修复后的逻辑对现有数据做确定性回填：
    新 stem = shared_material + "\n" + 原 stem（若材料已包含则跳过）

用法（backend 目录）：
    python -m scripts.backfill_chinese_material
"""
import asyncio
import json
import sys

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models import Document, Question, QuestionInstance

sys.stdout.reconfigure(encoding="utf-8")


def to_list(v):
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        try:
            p = json.loads(v)
            return p if isinstance(p, list) else []
        except Exception:
            return []
    return []


async def main() -> None:
    from app.core.config import settings

    engine = create_async_engine(settings.database_url, echo=False)
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with factory() as session:
            doc = await session.scalar(
                select(Document).where(Document.subject == "语文").order_by(Document.created_at.desc())
            )
            if doc is None:
                print("语文文档不存在")
                return
            task = await session.execute(
                text_select_task(doc.id)
            )
            row = task.fetchone()
            if row is None or row[0] is None:
                print("task result 不存在")
                return
            raw = row[0]
            tr = raw if isinstance(raw, dict) else json.loads(raw)
            pipeline_by_qn = {
                str(q.get("question_number")): q
                for q in tr.get("questions") or []
            }
            print(f"pipeline questions: {len(pipeline_by_qn)}")

            qrows = await session.execute(
                select(Question.id, QuestionInstance.source_question_number, Question.stem)
                .join(QuestionInstance, QuestionInstance.question_id == Question.id)
                .where(QuestionInstance.document_id == doc.id)
            )
            updated = 0
            skipped = 0
            for qid, qno, stem in qrows.all():
                pq = pipeline_by_qn.get(str(qno))
                if not pq:
                    continue
                shared = (pq.get("shared_material") or "").strip()
                if not shared:
                    continue
                if shared in (stem or ""):
                    skipped += 1
                    continue
                new_stem = shared + "\n" + (stem or "")
                await session.execute(
                    update(Question).where(Question.id == qid).values(stem=new_stem)
                )
                updated += 1
            await session.commit()
            print(f"回填: {updated} 题, 已含材料跳过: {skipped} 题")

            # 验证
            print("\n=== 回填后 stem 长度抽样 ===")
            rows2 = await session.execute(
                select(QuestionInstance.source_question_number, Question.stem)
                .join(Question, Question.id == QuestionInstance.question_id)
                .where(QuestionInstance.document_id == doc.id)
                .where(QuestionInstance.source_question_number.in_(("1", "8", "22", "24")))
                .order_by(QuestionInstance.source_question_number)
            )
            for qno, stem in rows2.all():
                print(f"  Q{qno}: stem_len={len(stem or '')} 前80={ (stem or '')[:80]!r}")
    finally:
        await engine.dispose()


def text_select_task(doc_id):
    from sqlalchemy import text
    return text(
        "SELECT result_json FROM background_tasks "
        "WHERE payload_json->>'document_id' = :did ORDER BY created_at DESC LIMIT 1"
    ).bindparams(did=str(doc_id))


if __name__ == "__main__":
    asyncio.run(main())

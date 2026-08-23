"""Phase 2A Step 6 DB 验证脚本。

在真实 PostgreSQL 上执行知识点映射并输出执行计划验证 SQL：
    SELECT kn.code, kn.name, qk.confidence, qk.mapping_source, qk.review_status
    FROM question_knowledge qk
    JOIN knowledge_nodes kn ON kn.id = qk.knowledge_node_id
    WHERE qk.question_id = '<question_id>';

用法（backend 目录）：
    python -m scripts.step6_db_verify
"""
import asyncio
import sys
import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.domains.knowledge.repository import (
    KnowledgeNodeRepository,
    QuestionTypeRepository,
)
from app.domains.knowledge.service import KnowledgeService
from app.models import (
    Document,
    Question,
    QuestionInstance,
    QuestionKnowledge,
    Subject,
)

sys.stdout.reconfigure(encoding="utf-8")


async def main() -> None:
    from app.core.config import settings

    engine = create_async_engine(settings.database_url, echo=False)
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    filename = f"step6_verify_{uuid.uuid4().hex[:6]}.pdf"
    subject_code_tmp = f"step6_verify_{uuid.uuid4().hex[:8]}"
    try:
        async with factory() as session:
            # MATH 学科（与知识树 seed 一致，复用已有）
            subj = await session.scalar(select(Subject).where(Subject.code == "MATH"))
            if subj is None:
                subj = Subject(code="MATH", name="数学")
                session.add(subj)
                await session.flush()

            doc = Document(filename=filename, file_type="pdf", object_key=f"test/{filename}",
                           subject="数学")
            session.add(doc)
            await session.flush()

            q = Question(
                subject_id=subj.id, stem="函数的单调性验证题", source_type="document",
                source_document_name=filename, status="approved", occurrence_count=1,
            )
            session.add(q)
            await session.flush()
            session.add(QuestionInstance(
                question_id=q.id, document_id=doc.id, source_type="document",
                source_document_name=filename, source_question_number="1", occurrence_no=1,
            ))
            await session.flush()

            svc = KnowledgeService(
                node_repository=KnowledgeNodeRepository(session),
                question_type_repository=QuestionTypeRepository(session),
            )
            written = await svc.map_question_to_knowledge(
                question_id=q.id,
                subject_id=subj.id,
                subject_code="MATH",
                subject_name="数学",
                knowledge_points=["函数单调性"],
            )
            assert len(written) >= 1, "映射应至少写入 1 条记录"
            await session.commit()

            print("=== 执行计划 Step 6 验证 SQL ===")
            rows = await session.execute(text("""
                SELECT kn.code, kn.name, qk.confidence, qk.mapping_source, qk.review_status
                FROM question_knowledge qk
                JOIN knowledge_nodes kn ON kn.id = qk.knowledge_node_id
                WHERE qk.question_id = :qid
            """), {"qid": str(q.id)})
            for r in rows:
                print(f"code={r[0]}  name={r[1]}  confidence={r[2]}  source={r[3]}  review={r[4]}")

            # 清理
            await session.execute(
                QuestionKnowledge.__table__.delete().where(QuestionKnowledge.question_id == q.id)
            )
            await session.execute(
                QuestionInstance.__table__.delete().where(QuestionInstance.question_id == q.id)
            )
            await session.execute(Question.__table__.delete().where(Question.id == q.id))
            await session.execute(Document.__table__.delete().where(Document.id == doc.id))
            if subj.code == "MATH":
                # 复用 seed 学科，不删除
                pass
            await session.commit()
            print()
            print("测试数据已清理（MATH 学科为 seed 复用，保留）")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

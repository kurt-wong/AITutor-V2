"""Phase 2A Step 2 DB 验证脚本。

在真实 PostgreSQL 上执行端到端审核写回，并输出执行计划要求的验证 SQL 结果：

    SELECT q.id, q.status, q.stem, q.answer
    FROM questions q
    JOIN question_instances qi ON qi.question_id = q.id
    WHERE qi.document_id = '<document_id>'
      AND qi.source_question_number = '<question_number>';

用法（backend 目录）：
    python scripts/step2_db_verify.py
"""
import asyncio
import sys
import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.application.services import DocumentApplicationService
from app.core.config import settings
from app.domains.document.repository import (
    DocumentProcessingLogRepository,
    DocumentRepository,
)
from app.domains.document.service import DocumentService
from app.domains.event.repository import DomainEventRepository
from app.domains.event.service import EventService
from app.domains.question.repository import QuestionRepository
from app.domains.question.service import QuestionService
from app.domains.task.repository import BackgroundTaskRepository
from app.domains.task.service import TaskService
from app.infrastructure.storage import MinIOStorage
from app.models import (
    BackgroundTask,
    Document,
    Question,
    QuestionInstance,
    Subject,
)

sys.stdout.reconfigure(encoding="utf-8")


async def main() -> None:
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    subject_code = f"step2_verify_{uuid.uuid4().hex[:8]}"
    filename = f"verify_{uuid.uuid4().hex[:6]}.pdf"
    document_id = None

    try:
        async with session_factory() as session:
            subj = Subject(code=subject_code, name="Step2 验证学科")
            session.add(subj)
            await session.flush()

            doc = Document(filename=filename, file_type="pdf", object_key=f"test/{filename}")
            session.add(doc)
            await session.flush()

            q = Question(
                subject_id=subj.id,
                stem="Step2 验证原题干",
                source_type="document",
                source_document_name=filename,
                status="reviewing",
                occurrence_count=1,
                answer="原答案",
                explanation="原详解",
            )
            session.add(q)
            await session.flush()

            inst = QuestionInstance(
                question_id=q.id,
                document_id=doc.id,
                source_type="document",
                source_document_name=filename,
                source_question_number="12",
                occurrence_no=1,
            )
            session.add(inst)
            await session.flush()

            task = BackgroundTask(
                task_type="document_parse",
                status="succeeded",
                progress=1,
                payload_json={"document_id": str(doc.id)},
                result_json={"status": "succeeded", "questions": [{"question_number": "12"}]},
            )
            session.add(task)
            await session.flush()

            document_id = doc.id
            qid = q.id

            # 构造真实服务并执行审核写回
            svc = DocumentApplicationService(
                document_service=DocumentService(
                    document_repository=DocumentRepository(session),
                    log_repository=DocumentProcessingLogRepository(session),
                ),
                task_service=TaskService(repository=BackgroundTaskRepository(session)),
                event_service=EventService(repository=DomainEventRepository(session)),
                storage=MinIOStorage(),
                question_service=QuestionService(repository=QuestionRepository(session)),
            )
            returned_task, error_code = await svc.update_document_review(
                doc.id,
                question_number="12",
                status="approved",
                comment="Step2 DB 验证",
                overrides={"stem": "Step2 修正后的题干", "answer": "D"},
            )
            assert error_code is None, f"error_code={error_code}"
            await session.commit()

            print("=" * 60)
            print("执行计划 Step 2 验证 SQL")
            print("=" * 60)
            rows = await session.execute(text("""
                SELECT q.id, q.status, q.stem, q.answer
                FROM questions q
                JOIN question_instances qi ON qi.question_id = q.id
                WHERE qi.document_id = :doc_id
                  AND qi.source_question_number = :qno
            """), {"doc_id": str(doc.id), "qno": "12"})
            for row in rows:
                print(f"question_id = {row[0]}")
                print(f"status      = {row[1]}")
                print(f"stem        = {row[2]}")
                print(f"answer      = {row[3]}")

            print()
            print("task.result_json 同步更新确认")
            print("=" * 60)
            task_row = await session.execute(
                select(BackgroundTask).where(
                    BackgroundTask.payload_json["document_id"].astext == str(doc.id)
                )
            )
            task_obj = task_row.scalar_one()
            print(f"review_decisions[12] = {task_obj.result_json['review_decisions']['12']}")
            print(f"review_overrides[12] = {task_obj.result_json['review_overrides']['12']}")

            # 清理
            await session.execute(
                QuestionInstance.__table__.delete().where(QuestionInstance.question_id == qid)
            )
            await session.execute(Question.__table__.delete().where(Question.id == qid))
            await session.execute(Document.__table__.delete().where(Document.id == doc.id))
            await session.execute(
                BackgroundTask.__table__.delete().where(
                    BackgroundTask.payload_json["document_id"].astext == str(doc.id)
                )
            )
            await session.execute(Subject.__table__.delete().where(Subject.code == subject_code))
            await session.commit()
            print()
            print("测试数据已清理")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

"""Phase 2A Step 4 DB 验证脚本。

在真实 PostgreSQL 上验证答案重试的精确关联：
    SELECT qi.document_id, qi.source_question_number, q.answer
    FROM question_instances qi
    JOIN questions q ON q.id = qi.question_id
    WHERE qi.document_id = '<document_id>'
    ORDER BY qi.source_question_number;

用法（backend 目录）：
    python -m scripts.step4_db_verify
"""
import asyncio
import sys
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.domains.document.answer_extractor import AnswerExtractionResult, ExtractedAnswer
from app.domains.document.retry_repository import AnswerExtractionRetryRepository
from app.models import (
    AnswerExtractionRetry,
    Document,
    Question,
    QuestionInstance,
)

sys.stdout.reconfigure(encoding="utf-8")


async def main() -> None:
    from app.core.config import settings

    engine = create_async_engine(settings.database_url, echo=False)
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    filename = f"step4_verify_{uuid.uuid4().hex[:6]}.pdf"
    subject_code = f"step4_verify_{uuid.uuid4().hex[:8]}"
    doc_id = None
    try:
        async with factory() as session:
            subj_id = uuid.uuid4()
            await session.execute(
                text("INSERT INTO subjects (id, code, name) VALUES (:id, :code, :name)"),
                {"id": subj_id, "code": subject_code, "name": "Step4 验证学科"},
            )

            doc = Document(
                filename=filename,
                file_type="pdf",
                object_key=f"test/{filename}",
                subject="数学",
                ocr_markdown="# 测试\n1. 题干一\n2. 题干二\n3. 题干三\n",
            )
            session.add(doc)
            await session.flush()
            doc_id = doc.id

            # 3 道空答案题
            qids = {}
            for qno in ["1", "2", "3"]:
                q = Question(
                    subject_id=subj_id, stem=f"第{qno}题", source_type="document",
                    source_document_name=filename, status="reviewing",
                    occurrence_count=1, answer=None,
                )
                session.add(q)
                await session.flush()
                qids[qno] = q.id
                session.add(QuestionInstance(
                    question_id=q.id, document_id=doc.id, source_type="document",
                    source_document_name=filename, source_question_number=qno, occurrence_no=1,
                ))
            item = AnswerExtractionRetry(document_id=doc.id, status="pending")
            session.add(item)
            await session.flush()

            # mock 答案提取
            answer_result = AnswerExtractionResult(subject="数学")
            for qno, ans in {"1": "A", "2": "B", "3": "C"}.items():
                answer_result.answers[qno] = ExtractedAnswer(
                    question_number=qno, answer=ans, explanation=f"{qno} 详解",
                )

            repo = AnswerExtractionRetryRepository(session)
            from app.worker.answer_retry_worker import _process_one_retry
            with patch(
                "app.worker.answer_retry_worker.extract_answers_from_markdown",
                AsyncMock(return_value=answer_result),
            ):
                await _process_one_retry(session, repo, item, MagicMock())

            print("=== 执行计划 Step 4 验证 SQL ===")
            rows = await session.execute(text("""
                SELECT qi.document_id, qi.source_question_number, q.answer
                FROM question_instances qi
                JOIN questions q ON q.id = qi.question_id
                WHERE qi.document_id = :doc_id
                ORDER BY qi.source_question_number
            """), {"doc_id": str(doc.id)})
            for row in rows:
                print(f"document_id={row[0]}  question_number={row[1]}  answer={row[2]}")

            print()
            print(f"retry status = {item.status}")

            # 清理
            await session.execute(
                QuestionInstance.__table__.delete().where(
                    QuestionInstance.document_id == doc.id
                )
            )
            await session.execute(
                Question.__table__.delete().where(Question.id.in_(qids.values()))
            )
            await session.execute(
                AnswerExtractionRetry.__table__.delete().where(AnswerExtractionRetry.document_id == doc.id)
            )
            await session.execute(Document.__table__.delete().where(Document.id == doc.id))
            await session.execute(
                text("DELETE FROM subjects WHERE code = :code"), {"code": subject_code}
            )
            await session.commit()
            print()
            print("测试数据已清理")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

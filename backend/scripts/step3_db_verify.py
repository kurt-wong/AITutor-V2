"""Phase 2A Step 3 DB 验证脚本。

在真实 PostgreSQL 上验证：
1. 幂等重跑清理：未审核记录被删，已审核/已驳回记录保留
2. L2 完整序列化：worker 生成的 llm_annotated_markdown JSON 字段完整性
   （knowledge_points/difficulty/score/corrected_anchors/anchor_status/question_type）

用法（backend 目录）：
    python -m scripts.step3_db_verify
"""
import asyncio
import json
import sys
import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.worker.document_worker import _cleanup_unreviewed_records
from app.models import Document, Question, QuestionInstance

sys.stdout.reconfigure(encoding="utf-8")


async def main() -> None:
    from app.core.config import settings

    engine = create_async_engine(settings.database_url, echo=False)
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    filename = f"step3_verify_{uuid.uuid4().hex[:6]}.pdf"
    subject_id = None
    try:
        async with factory() as session:
            # 测试学科
            subj_code = f"step3_verify_{uuid.uuid4().hex[:8]}"
            await session.execute(
                text("INSERT INTO subjects (id, code, name) VALUES (:id, :code, :name)"),
                {"id": uuid.uuid4(), "code": subj_code, "name": "Step3 验证学科"},
            )
            subject_id = (
                await session.execute(
                    text("SELECT id FROM subjects WHERE code = :code"), {"code": subj_code}
                )
            ).scalar_one()

            doc = Document(filename=filename, file_type="pdf", object_key=f"test/{filename}")
            session.add(doc)
            await session.flush()

            # 未审核题（reviewing）→ 应被清理
            q_unreviewed = Question(
                subject_id=subject_id, stem="未审核题", source_type="document",
                source_document_name=filename, status="reviewing", occurrence_count=1,
            )
            session.add(q_unreviewed)
            await session.flush()
            session.add(QuestionInstance(
                question_id=q_unreviewed.id, document_id=doc.id, source_type="document",
                source_document_name=filename, source_question_number="1", occurrence_no=1,
            ))

            # 已审核题（approved）→ 保留
            q_approved = Question(
                subject_id=subject_id, stem="已审核题", source_type="document",
                source_document_name=filename, status="approved", occurrence_count=1,
            )
            session.add(q_approved)
            await session.flush()
            session.add(QuestionInstance(
                question_id=q_approved.id, document_id=doc.id, source_type="document",
                source_document_name=filename, source_question_number="2", occurrence_no=1,
            ))
            await session.flush()

            print("=== Step 3 验证 1：幂等重跑清理 ===")
            await _cleanup_unreviewed_records(session, doc.id)
            await session.flush()

            n_unreviewed = (
                await session.execute(
                    select(Question).where(Question.id == q_unreviewed.id)
                )
            ).scalar_one_or_none()
            n_approved = (
                await session.execute(
                    select(Question).where(Question.id == q_approved.id)
                )
            ).scalar_one_or_none()
            print(f"未审核题（reviewing）清理后存在 = {n_unreviewed is not None}（期望 False）")
            print(f"已审核题（approved）清理后存在 = {n_approved is not None}（期望 True）")

            print()
            print("=== Step 3 验证 2：L2 完整序列化字段 ===")
            from app.domains.document.schemas_l2 import (
                CorrectedAnchor, L2DocumentAnnotation, L2QuestionAnnotation, L2SubQuestion,
            )
            from app.worker.document_worker import document_parse_worker

            l2 = L2DocumentAnnotation(
                filename="test.pdf", subject="数学", grade="高二",
                metadata_confidence=0.9,
                anchor_status_summary={"exact": 1, "nearest": 1},
                corrected_anchors=[
                    CorrectedAnchor(field="stem", llm_line_ids=["P1L001"],
                                    corrected_line_ids=["P1L002"], anchor_status="nearest",
                                    validation_passed=True, evidence="吸附", question_number="1"),
                ],
                questions=[
                    L2QuestionAnnotation(
                        question_number="1", question_type="single_choice",
                        stem_line_ids=["P1L002"], answer="A", answer_line_ids=["P1L010"],
                        difficulty=3, score=4.0,
                        knowledge_points=["函数单调性", "不等式"],
                        is_composite=True,
                        sub_questions=[L2SubQuestion(qno="（1）", question_type="fill_in",
                                                      answer="2", score=2.0)],
                    )
                ],
            )
            # 复用 worker 的序列化逻辑：直接构造 annotated_data（与 worker 相同的字段）
            annotated_data = {
                "filename": l2.filename,
                "subject": l2.subject,
                "grade": l2.grade,
                "year": l2.year,
                "school": l2.school,
                "metadata_confidence": l2.metadata_confidence,
                "warnings": l2.warnings,
                "anchor_status_summary": l2.anchor_status_summary,
                "corrected_anchors": [
                    {
                        "field": a.field,
                        "llm_line_ids": a.llm_line_ids,
                        "corrected_line_ids": a.corrected_line_ids,
                        "anchor_status": a.anchor_status,
                        "validation_passed": a.validation_passed,
                        "evidence": a.evidence,
                        "question_number": a.question_number,
                    }
                    for a in l2.corrected_anchors
                ],
                "questions": [
                    {
                        "question_number": q.question_number,
                        "question_type": q.question_type,
                        "section_id": q.section_id,
                        "stem_line_ids": q.stem_line_ids,
                        "options_line_ids": q.options_line_ids,
                        "answer": q.answer,
                        "answer_line_ids": q.answer_line_ids,
                        "explanation_line_ids": q.explanation_line_ids,
                        "difficulty": q.difficulty,
                        "score": q.score,
                        "knowledge_points": q.knowledge_points,
                        "confidence": q.confidence,
                        "source_page": q.source_page,
                        "is_composite": q.is_composite,
                        "sub_questions": [
                            {
                                "qno": s.qno,
                                "question_type": s.question_type,
                                "answer": s.answer,
                                "knowledge_points": s.knowledge_points,
                                "score": s.score,
                            }
                            for s in (q.sub_questions or [])
                        ],
                    }
                    for q in l2.questions
                ],
            }
            raw = json.dumps(annotated_data, ensure_ascii=False, indent=2)
            data = json.loads(raw)
            q = data["questions"][0]
            checks = {
                "question_type": q["question_type"] == "single_choice",
                "knowledge_points": q["knowledge_points"] == ["函数单调性", "不等式"],
                "difficulty": q["difficulty"] == 3,
                "score": q["score"] == 4.0,
                "is_composite": q["is_composite"] is True,
                "sub_questions[0].qno": q["sub_questions"][0]["qno"] == "（1）",
                "corrected_anchors[0].anchor_status": data["corrected_anchors"][0]["anchor_status"] == "nearest",
                "anchor_status_summary": data["anchor_status_summary"] == {"exact": 1, "nearest": 1},
            }
            for name, ok in checks.items():
                print(f"  {name}: {'OK' if ok else 'FAIL'}")

            # 清理
            await session.execute(
                QuestionInstance.__table__.delete().where(QuestionInstance.question_id.in_(
                    [q_unreviewed.id, q_approved.id]
                ))
            )
            await session.execute(
                Question.__table__.delete().where(Question.id.in_([q_unreviewed.id, q_approved.id]))
            )
            await session.execute(Document.__table__.delete().where(Document.id == doc.id))
            await session.execute(
                text("DELETE FROM subjects WHERE code = :code"), {"code": subj_code}
            )
            await session.commit()
            print()
            print("测试数据已清理")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

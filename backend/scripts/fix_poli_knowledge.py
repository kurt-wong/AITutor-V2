"""重新映射 28 题政治知识点（修复 MATH-UNKNOWN 污染，2026-08-25）。

背景：ingestion 时 subject 为空名 → subject_code 回退 MATH → 28 题被映射到
MATH-UNKNOWN 节点（且该节点挂在垃圾 subject 英语(A班) 下）。

步骤：
1. 读政治文档 L2 → 每题的 knowledge_points
2. 删除 28 题现有 question_knowledge（MATH-UNKNOWN）
3. 用 KnowledgeService 按 POLI 学科重映射
4. 清理孤儿 MATH-UNKNOWN 节点与英语(A班) subject

用法（backend 目录）：
    python -m scripts.fix_poli_knowledge
"""
import asyncio
import json
import sys

from sqlalchemy import delete, select, text
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

MATH_UNKNOWN_NODE = "f5ea290c-9b94-418b-ac66-05757bbb8c22"
ENG_CLASS_SUBJECT = "df779f82-c9aa-4817-9061-568cf3573060"  # 英语(A班) 垃圾行


async def main() -> None:
    from app.core.config import settings

    engine = create_async_engine(settings.database_url, echo=False)
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with factory() as session:
            # 政治 subject（canonical）
            poli = await session.scalar(select(Subject).where(Subject.name == "政治"))
            if poli is None:
                print("政治 subject 不存在，中止")
                return

            # 1. 政治文档 + L2 knowledge_points
            doc = await session.scalar(
                select(Document).where(Document.subject == "政治").order_by(Document.created_at.desc())
            )
            if doc is None:
                print("政治文档不存在，中止")
                return
            l2 = json.loads(doc.llm_annotated_markdown or "{}")
            kp_by_qn: dict[str, list[str]] = {}
            for q in l2.get("questions") or []:
                kp = q.get("knowledge_points") or []
                if kp:
                    kp_by_qn[str(q.get("question_number"))] = list(kp)
            print(f"L2 带 knowledge_points 的题数: {len(kp_by_qn)}")

            # 2. 该文档的 28 题
            qrows = await session.execute(
                select(Question.id, QuestionInstance.source_question_number)
                .join(QuestionInstance, QuestionInstance.question_id == Question.id)
                .where(QuestionInstance.document_id == doc.id)
            )
            questions = list(qrows.all())
            print(f"文档题目数: {len(questions)}")

            svc = KnowledgeService(
                node_repository=KnowledgeNodeRepository(session),
                question_type_repository=QuestionTypeRepository(session),
            )

            remapped = 0
            no_kp = 0
            for qid, qno in questions:
                kp = kp_by_qn.get(str(qno)) or []
                # 删除旧映射（MATH-UNKNOWN 污染）
                await session.execute(
                    QuestionKnowledge.__table__.delete().where(
                        QuestionKnowledge.question_id == qid
                    )
                )
                if not kp:
                    no_kp += 1
                    continue
                await svc.map_question_to_knowledge(
                    question_id=qid,
                    subject_id=poli.id,
                    subject_code="POLI",
                    subject_name="政治",
                    knowledge_points=kp,
                )
                remapped += 1
            await session.commit()
            print(f"重映射: {remapped} 题, 无 knowledge_points: {no_kp} 题")

            # 3. 验证新映射
            print("\n=== 重映射后 question_knowledge 分布 ===")
            rows = await session.execute(text("""
                SELECT kn.code, kn.name, COUNT(*) AS n, qk.review_status
                FROM question_knowledge qk
                JOIN questions q ON q.id = qk.question_id
                JOIN knowledge_nodes kn ON kn.id = qk.knowledge_node_id
                WHERE q.subject_id = :subj
                GROUP BY kn.code, kn.name, qk.review_status
                ORDER BY n DESC
            """), {"subj": str(poli.id)})
            for r in rows:
                print(f"  {r[0]} {r[1]} n={r[2]} review={r[3]}")

            # 4. 清理孤儿 MATH-UNKNOWN 节点 + 英语(A班) subject
            still = await session.scalar(
                select(QuestionKnowledge).where(
                    QuestionKnowledge.knowledge_node_id == MATH_UNKNOWN_NODE
                )
            )
            if still is None:
                await session.execute(
                    text("DELETE FROM knowledge_nodes WHERE id = :nid"),
                    {"nid": MATH_UNKNOWN_NODE},
                )
                print("\nMATH-UNKNOWN 节点已删除（无引用）")
            else:
                print("\nMATH-UNKNOWN 节点仍有引用，保留")
            eng_class = await session.scalar(
                select(Subject).where(Subject.id == ENG_CLASS_SUBJECT)
            )
            if eng_class is not None:
                node_left = await session.scalar(
                    text("SELECT COUNT(*) FROM knowledge_nodes WHERE subject_id = :sid"),
                    {"sid": ENG_CLASS_SUBJECT},
                )
                q_left = await session.scalar(
                    text("SELECT COUNT(*) FROM questions WHERE subject_id = :sid"),
                    {"sid": ENG_CLASS_SUBJECT},
                )
                if int(node_left or 0) == 0 and int(q_left or 0) == 0:
                    await session.execute(
                        text("DELETE FROM subjects WHERE id = :sid"),
                        {"sid": ENG_CLASS_SUBJECT},
                    )
                    print("英语(A班) subject 已删除（无引用）")
                else:
                    print(f"英语(A班) 仍有引用 nodes={node_left} questions={q_left}，保留")
            await session.commit()
            print("\n完成")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

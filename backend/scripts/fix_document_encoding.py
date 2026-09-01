"""数据回填脚本 — 修复已入库文档的 GBK mojibake 编码问题。

用法：
    cd backend && python scripts/fix_document_encoding.py

功能：
    1. 扫描 documents 表中的乱码记录
    2. 修复 filename、subject、grade 字段
    3. 同步修复 questions.source_document_name
    4. 同步修复 questions.subject_id（映射到正确科目）
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.core.database import engine
from app.utils.encoding import is_gbk_mojibake, fix_gbk_mojibake


async def get_subject_id_map(conn) -> dict[str, str]:
    """获取科目名称到 ID 的映射。"""
    result = await conn.execute(text("SELECT id, name FROM subjects"))
    return {row[1]: str(row[0]) for row in result.fetchall()}


async def fix_documents():
    """修复 documents 表中的乱码记录。"""
    async with engine.begin() as conn:
        # 获取科目映射
        subject_id_map = await get_subject_id_map(conn)
        print(f"Subject ID map: {subject_id_map}")

        # 查询所有文档
        result = await conn.execute(text("""
            SELECT id, filename, subject, grade
            FROM documents
        """))
        documents = result.fetchall()

        fixed_count = 0
        for doc in documents:
            doc_id, filename, subject, grade = doc

            # 检查是否需要修复
            needs_fix = False
            fixed_filename = filename
            fixed_subject = subject
            fixed_grade = grade

            if filename and is_gbk_mojibake(filename):
                fixed_filename = fix_gbk_mojibake(filename)
                needs_fix = True

            if subject and is_gbk_mojibake(subject):
                fixed_subject = fix_gbk_mojibake(subject)
                needs_fix = True

            if grade and is_gbk_mojibake(grade):
                fixed_grade = fix_gbk_mojibake(grade)
                needs_fix = True

            if needs_fix:
                # 更新 documents 表
                await conn.execute(text("""
                    UPDATE documents
                    SET filename = :filename, subject = :subject, grade = :grade
                    WHERE id = :id
                """), {
                    "id": doc_id,
                    "filename": fixed_filename,
                    "subject": fixed_subject,
                    "grade": fixed_grade,
                })

                # 同步修复 questions.source_document_name
                if filename != fixed_filename:
                    await conn.execute(text("""
                        UPDATE questions
                        SET source_document_name = :new_name
                        WHERE source_document_name = :old_name
                    """), {
                        "old_name": filename,
                        "new_name": fixed_filename,
                    })

                # 同步修复 questions.subject_id
                if subject != fixed_subject and fixed_subject in subject_id_map:
                    new_subject_id = subject_id_map[fixed_subject]
                    # 通过 question_instances 找到该文档下的所有题目
                    await conn.execute(text("""
                        UPDATE questions
                        SET subject_id = :new_subject_id
                        WHERE id IN (
                            SELECT DISTINCT qi.question_id
                            FROM question_instances qi
                            WHERE qi.document_id = :doc_id
                        )
                    """), {
                        "doc_id": doc_id,
                        "new_subject_id": new_subject_id,
                    })
                    print(f"  Updated questions.subject_id to {new_subject_id} ({fixed_subject})")

                print(f"Fixed document {doc_id}:")
                if filename != fixed_filename:
                    print(f"  filename: fixed")
                if subject != fixed_subject:
                    print(f"  subject: fixed")
                if grade != fixed_grade:
                    print(f"  grade: fixed")

                fixed_count += 1

        print(f"\nTotal documents: {len(documents)}")
        print(f"Fixed documents: {fixed_count}")


async def main():
    """主函数。"""
    print("Starting document encoding fix...")
    await fix_documents()
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())

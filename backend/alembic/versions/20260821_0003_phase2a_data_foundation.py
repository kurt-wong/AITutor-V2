"""Phase 2A: data foundation — Question/Instance/QuestionKnowledge schema changes

Revision ID: 20260821_0003
Revises: 3d7ee1cb7c3a
Create Date: 2026-08-21

Phase 2A Step 1 changes:
- questions: add content_hash, remove year/school, update index
- question_instances: add document_id FK + backfill + unique constraint
- question_knowledge: add mapping_source, review_status

Data backfill order is critical:
1. Add document_id (nullable)
2. Backfill from source_document_name = documents.filename
3. Backfill year/school from questions table
4. Set NOT NULL
5. Add unique constraint
6. Drop questions.year/school
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "20260821_0003"
down_revision = "3d7ee1cb7c3a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Step 1: questions 表变更 ──────────────────────────────────

    # 新增 content_hash（Step 5 实现 hash 逻辑，本步只加列）
    op.add_column("questions", sa.Column("content_hash", sa.String(64), nullable=True))

    # 更新索引：移除 year，保留 subject_id + grade
    op.drop_index("ix_questions_subject_grade_year", table_name="questions")
    op.create_index("ix_questions_subject_grade", "questions", ["subject_id", "grade"])
    op.create_index("ix_questions_content_hash", "questions", ["content_hash"])

    # ── Step 2: question_instances 新增 document_id ──────────────

    # 2a: 新增 document_id（nullable，先不加约束）
    op.add_column(
        "question_instances",
        sa.Column("document_id", sa.Uuid(), sa.ForeignKey("documents.id"), nullable=True),
    )
    op.create_index(
        "ix_question_instances_document_id",
        "question_instances",
        ["document_id"],
    )

    # 2b: 回填 document_id（source_document_name = documents.filename）
    op.execute("""
        UPDATE question_instances qi
        SET document_id = d.id
        FROM documents d
        WHERE qi.source_document_name = d.filename
          AND qi.document_id IS NULL
    """)

    # 2c: 回填 year/school 到 question_instances（从 questions 表迁移已有数据）
    # COALESCE 保证：只填充 NULL 字段，不覆盖已有值
    op.execute("""
        UPDATE question_instances qi
        SET year = COALESCE(qi.year, q.year),
            school = COALESCE(qi.school, q.school)
        FROM questions q
        WHERE qi.question_id = q.id
          AND (qi.year IS NULL OR qi.school IS NULL)
    """)

    # 2d: 设置 NOT NULL（回填完成后，所有 document-sourced 的 Instance 都有 document_id）
    op.alter_column(
        "question_instances",
        "document_id",
        nullable=False,
        existing_type=sa.Uuid(),
    )

    # 2e: 唯一约束 (document_id, source_question_number)
    # 部分唯一索引：只对 source_question_number 非 NULL 的记录生效
    op.execute("""
        CREATE UNIQUE INDEX ix_question_instances_doc_qno
        ON question_instances (document_id, source_question_number)
        WHERE source_question_number IS NOT NULL
    """)

    # ── Step 3: 移除 questions.year / questions.school ──────────

    # 先确认数据已迁移到 question_instances
    op.drop_column("questions", "year")
    op.drop_column("questions", "school")

    # ── Step 4: question_knowledge 新增字段 ──────────────────────

    op.add_column(
        "question_knowledge",
        sa.Column("mapping_source", sa.String(20), nullable=True),
    )
    op.add_column(
        "question_knowledge",
        sa.Column(
            "review_status",
            sa.String(20),
            server_default="approved",
            nullable=False,
        ),
    )


def downgrade() -> None:
    """逆向迁移：恢复列和索引结构。

    注意：downgrade 只恢复 schema 结构，不恢复数据：
    - questions.year/school 恢复为空列（upgrade 时迁移到 question_instances 的数据丢失）
    - question_instances.document_id 被移除（回填数据丢失）
    - question_knowledge.mapping_source/review_status 被移除

    如需保留数据，请在 downgrade 前手动备份。
    """
    # question_knowledge
    op.drop_column("question_knowledge", "review_status")
    op.drop_column("question_knowledge", "mapping_source")

    # questions: 恢复 year/school
    op.add_column("questions", sa.Column("school", sa.String(255), nullable=True))
    op.add_column("questions", sa.Column("year", sa.Integer(), nullable=True))

    # question_instances: 移除唯一约束和 document_id
    op.drop_index("ix_question_instances_doc_qno", table_name="question_instances")
    op.drop_index("ix_question_instances_document_id", table_name="question_instances")
    op.drop_column("question_instances", "document_id")

    # questions: 恢复索引和移除 content_hash
    op.drop_index("ix_questions_content_hash", table_name="questions")
    op.drop_index("ix_questions_subject_grade", table_name="questions")
    op.create_index(
        "ix_questions_subject_grade_year",
        "questions",
        ["subject_id", "grade", "year"],
    )
    op.drop_column("questions", "content_hash")

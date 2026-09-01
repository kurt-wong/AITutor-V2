"""add question_candidates table for admission gate

Revision ID: 20260831_0001
Revises: 20260830_0001
Create Date: 2026-08-31
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "20260831_0001"
down_revision = "20260830_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "question_candidates",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("subject_id", sa.Uuid(as_uuid=True), sa.ForeignKey("subjects.id"), index=True, nullable=False),
        sa.Column("grade", sa.String(50), nullable=True),
        sa.Column("question_type_id", sa.Uuid(as_uuid=True), sa.ForeignKey("question_types.id"), index=True, nullable=True),
        sa.Column("score", sa.Numeric(8, 2), nullable=True),
        sa.Column("difficulty", sa.Integer, nullable=True),
        sa.Column("stem", sa.Text, nullable=False),
        sa.Column("options", JSONB(), nullable=True),
        sa.Column("answer", sa.Text, nullable=True),
        sa.Column("answer_structure", JSONB(), nullable=True),
        sa.Column("word_bank", JSONB(), nullable=True),
        sa.Column("explanation", sa.Text, nullable=True),
        sa.Column("source_type", sa.String(20), server_default="document"),
        sa.Column("source_document_name", sa.String(255), nullable=True),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("is_composite", sa.Boolean, server_default=sa.text("false")),
        sa.Column("original_question_type", sa.String(50), nullable=True),
        sa.Column("section_id", sa.String(100), nullable=True),
        sa.Column("sub_questions", JSONB(), nullable=True),
        # 展示契约 v0.4 字段
        sa.Column("stem_line_ids", JSONB(), nullable=True),
        sa.Column("answer_line_ids", JSONB(), nullable=True),
        sa.Column("explanation_line_ids", JSONB(), nullable=True),
        sa.Column("shared_material_line_ids", JSONB(), nullable=True),
        sa.Column("shared_material_notes_line_ids", JSONB(), nullable=True),
        sa.Column("stem_region", JSONB(), nullable=True),
        sa.Column("answer_region", JSONB(), nullable=True),
        sa.Column("explanation_region", JSONB(), nullable=True),
        sa.Column("scoring_standard", sa.Text, nullable=True),
        sa.Column("shared_material", sa.Text, nullable=True),
        sa.Column("shared_material_notes", sa.Text, nullable=True),
        sa.Column("answer_images", JSONB(), nullable=True),
        # Admission Gate 专属字段
        sa.Column("gate_decision", sa.String(20), nullable=False),
        sa.Column("gate_reason", sa.String(200), nullable=True),
        sa.Column("gate_checks", JSONB(), nullable=True),
        sa.Column("admission_version", sa.String(50), server_default="1.0"),
        sa.Column("document_id", sa.Uuid(as_uuid=True), sa.ForeignKey("documents.id"), index=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_index("ix_question_candidates_document", "question_candidates", ["document_id"])
    op.create_index("ix_question_candidates_gate_decision", "question_candidates", ["gate_decision"])
    op.create_index(
        "ix_question_candidates_doc_hash",
        "question_candidates",
        ["document_id", "content_hash"],
        unique=True,
        postgresql_where=sa.text("content_hash IS NOT NULL"),
    )

    # ── 数据迁移：将现有 reviewing 题目迁移到 question_candidates ──
    # 注意：不能依赖 filename 反查 document_id（可能不匹配），
    # 改用 question_instances.document_id 关联。
    # 同时需先删除依赖记录，再删 Question 本身。

    # 1. 迁移有 instance 关联的 reviewing 题目
    op.execute("""
        INSERT INTO question_candidates (
            id, subject_id, grade, question_type_id, score, difficulty,
            stem, options, answer, answer_structure, word_bank, explanation,
            source_type, source_document_name, confidence, content_hash,
            is_composite, original_question_type, section_id, sub_questions,
            stem_line_ids, answer_line_ids, explanation_line_ids,
            shared_material_line_ids, shared_material_notes_line_ids,
            stem_region, answer_region, explanation_region,
            scoring_standard, shared_material, shared_material_notes,
            answer_images,
            gate_decision, gate_reason, gate_checks, admission_version,
            document_id, created_at, updated_at
        )
        SELECT DISTINCT ON (q.id)
            gen_random_uuid(), q.subject_id, q.grade, q.question_type_id,
            q.score, q.difficulty,
            q.stem, q.options, q.answer, q.answer_structure, q.word_bank,
            q.explanation,
            q.source_type, q.source_document_name, q.confidence, q.content_hash,
            q.is_composite, q.original_question_type, q.section_id, q.sub_questions,
            q.stem_line_ids, q.answer_line_ids, q.explanation_line_ids,
            q.shared_material_line_ids, q.shared_material_notes_line_ids,
            q.stem_region, q.answer_region, q.explanation_region,
            q.scoring_standard, q.shared_material, q.shared_material_notes,
            q.answer_images,
            'review', COALESCE(q.review_reason, 'migrated_from_reviewing'),
            '[]'::jsonb, '1.0',
            qi.document_id,
            q.created_at, q.updated_at
        FROM questions q
        JOIN question_instances qi ON qi.question_id = q.id
        WHERE q.status = 'reviewing'
    """)

    # 2. 删除依赖记录（先删子表，再删主表）
    op.execute("""
        DELETE FROM question_knowledge
        WHERE question_id IN (SELECT id FROM questions WHERE status = 'reviewing')
    """)
    op.execute("""
        DELETE FROM question_embeddings
        WHERE question_id IN (SELECT id FROM questions WHERE status = 'reviewing')
    """)
    op.execute("""
        DELETE FROM question_images
        WHERE question_id IN (SELECT id FROM questions WHERE status = 'reviewing')
    """)
    op.execute("""
        DELETE FROM question_instances
        WHERE question_id IN (SELECT id FROM questions WHERE status = 'reviewing')
    """)

    # 3. 删除已迁移的 reviewing 题目
    op.execute("DELETE FROM questions WHERE status = 'reviewing'")


def downgrade() -> None:
    op.drop_index("ix_question_candidates_doc_hash", table_name="question_candidates")
    op.drop_index("ix_question_candidates_gate_decision", table_name="question_candidates")
    op.drop_index("ix_question_candidates_document", table_name="question_candidates")
    op.drop_table("question_candidates")

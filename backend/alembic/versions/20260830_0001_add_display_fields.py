"""add display contract fields to questions

Revision ID: 20260830_0001
Revises: 20260829_0004
Create Date: 2026-08-30
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "20260830_0001"
down_revision = "20260829_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 行号引用（JSONB）
    op.add_column("questions", sa.Column("stem_line_ids", JSONB(), nullable=True))
    op.add_column("questions", sa.Column("answer_line_ids", JSONB(), nullable=True))
    op.add_column("questions", sa.Column("explanation_line_ids", JSONB(), nullable=True))
    op.add_column("questions", sa.Column("shared_material_line_ids", JSONB(), nullable=True))
    op.add_column("questions", sa.Column("shared_material_notes_line_ids", JSONB(), nullable=True))

    # 区域标记（JSONB）- 仅 golden 校验和切片元数据
    op.add_column("questions", sa.Column("stem_region", JSONB(), nullable=True))
    op.add_column("questions", sa.Column("answer_region", JSONB(), nullable=True))
    op.add_column("questions", sa.Column("explanation_region", JSONB(), nullable=True))

    # 内容字段（Text）
    op.add_column("questions", sa.Column("scoring_standard", sa.Text(), nullable=True))
    op.add_column("questions", sa.Column("shared_material", sa.Text(), nullable=True))
    op.add_column("questions", sa.Column("shared_material_notes", sa.Text(), nullable=True))

    # 图片关联（JSONB）
    op.add_column("questions", sa.Column("answer_images", JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("questions", "answer_images")
    op.drop_column("questions", "shared_material_notes")
    op.drop_column("questions", "shared_material")
    op.drop_column("questions", "scoring_standard")
    op.drop_column("questions", "explanation_region")
    op.drop_column("questions", "answer_region")
    op.drop_column("questions", "stem_region")
    op.drop_column("questions", "shared_material_notes_line_ids")
    op.drop_column("questions", "shared_material_line_ids")
    op.drop_column("questions", "explanation_line_ids")
    op.drop_column("questions", "answer_line_ids")
    op.drop_column("questions", "stem_line_ids")

"""add question image sub question binding

Revision ID: 20260829_0003
Revises: 20260829_0002
Create Date: 2026-08-29
"""
from alembic import op
import sqlalchemy as sa


revision = "20260829_0003"
down_revision = "20260829_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("question_images", sa.Column("sub_question_qno", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("question_images", "sub_question_qno")

"""preserve original question type and section

Revision ID: 20260828_0001
Revises: 20260827_0001
Create Date: 2026-08-28
"""
from alembic import op
import sqlalchemy as sa

revision = "20260828_0001"
down_revision = "20260827_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("questions", sa.Column("original_question_type", sa.String(50), nullable=True))
    op.add_column("questions", sa.Column("section_id", sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column("questions", "section_id")
    op.drop_column("questions", "original_question_type")

"""add level description keywords to question_types

Revision ID: 20260829_0004
Revises: 20260829_0003
Create Date: 2026-08-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "20260829_0004"
down_revision = "20260829_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("question_types", sa.Column("level", sa.Integer(), nullable=False, server_default="3"))
    op.add_column("question_types", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("question_types", sa.Column("keywords", JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("question_types", "keywords")
    op.drop_column("question_types", "description")
    op.drop_column("question_types", "level")

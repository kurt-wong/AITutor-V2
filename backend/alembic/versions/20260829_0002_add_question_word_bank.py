"""add question word_bank

Revision ID: 20260829_0002
Revises: 20260829_0001
Create Date: 2026-08-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "20260829_0002"
down_revision = "20260829_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("questions", sa.Column("word_bank", JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("questions", "word_bank")

"""add question_images url column

Revision ID: 20260827_0001
Revises: 20260821_0005
Create Date: 2026-08-27
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '20260827_0001'
down_revision = '20260821_0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # QuestionImage 新增 url 列（OCR 图片 URL，2026-08-27）
    op.add_column('question_images', sa.Column('url', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('question_images', 'url')

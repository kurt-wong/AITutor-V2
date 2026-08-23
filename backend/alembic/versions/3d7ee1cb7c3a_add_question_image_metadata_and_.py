"""add question_image metadata and question composite fields

Revision ID: 3d7ee1cb7c3a
Revises: 
Create Date: 2026-08-20
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '3d7ee1cb7c3a'
down_revision = '20260810_0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Document 新增字段：三份文档持久化
    op.add_column('documents', sa.Column('native_markdown', sa.Text(), nullable=True))
    op.add_column('documents', sa.Column('ocr_markdown', sa.Text(), nullable=True))
    op.add_column('documents', sa.Column('llm_annotated_markdown', sa.Text(), nullable=True))

    # QuestionImage 新增字段
    op.add_column('question_images', sa.Column('page_no', sa.Integer(), nullable=True))
    op.add_column('question_images', sa.Column('bbox', postgresql.JSONB(), nullable=True))
    op.add_column('question_images', sa.Column('placement', sa.String(30), nullable=True))
    op.add_column('question_images', sa.Column('source', sa.String(30), nullable=True))
    op.add_column('question_images', sa.Column('figure_id', sa.String(100), nullable=True))

    # Question 新增字段
    op.add_column('questions', sa.Column('is_composite', sa.Boolean(), server_default='false', nullable=True))
    op.add_column('questions', sa.Column('sub_questions', postgresql.JSONB(), nullable=True))
    op.add_column('questions', sa.Column('review_reason', sa.String(200), nullable=True))

    # 答案提取重试队列表
    op.create_table(
        'answer_extraction_retries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id'), nullable=False),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('background_tasks.id'), nullable=True),
        sa.Column('error_detail', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('max_retries', sa.Integer(), server_default='3', nullable=False),
        sa.Column('status', sa.String(20), server_default='pending', nullable=False),
        sa.Column('last_retry_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_answer_retries_status', 'answer_extraction_retries', ['status', 'created_at'])
    op.create_index('ix_answer_retries_document', 'answer_extraction_retries', ['document_id'])


def downgrade() -> None:
    op.drop_table('answer_extraction_retries')
    op.drop_column('questions', 'review_reason')
    op.drop_column('questions', 'sub_questions')
    op.drop_column('questions', 'is_composite')
    op.drop_column('question_images', 'figure_id')
    op.drop_column('question_images', 'source')
    op.drop_column('question_images', 'placement')
    op.drop_column('question_images', 'bbox')
    op.drop_column('question_images', 'page_no')
    op.drop_column('documents', 'llm_annotated_markdown')
    op.drop_column('documents', 'ocr_markdown')
    op.drop_column('documents', 'native_markdown')

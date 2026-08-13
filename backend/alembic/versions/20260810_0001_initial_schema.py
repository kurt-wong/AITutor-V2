"""initial schema

Revision ID: 20260810_0001
Revises:
Create Date: 2026-08-10 22:50:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "20260810_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("username", sa.String(length=100), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "subjects",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("code", sa.String(length=50), nullable=False, unique=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_type", sa.String(length=10), nullable=False),
        sa.Column("object_key", sa.String(length=500), nullable=False),
        sa.Column("subject", sa.String(length=50)),
        sa.Column("grade", sa.String(length=50)),
        sa.Column("year", sa.Integer()),
        sa.Column("school", sa.String(length=255)),
        sa.Column("upload_status", sa.String(length=30), server_default="queued"),
        sa.Column("processing_status", sa.String(length=30), server_default="pending"),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "document_processing_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("document_id", sa.Uuid(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("stage", sa.String(length=100), nullable=False),
        sa.Column("message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "question_types",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("subject_id", sa.Uuid(), sa.ForeignKey("subjects.id"), nullable=False),
        sa.Column("parent_id", sa.Uuid(), sa.ForeignKey("question_types.id")),
        sa.Column("code", sa.String(length=100), nullable=False, unique=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "knowledge_nodes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("subject_id", sa.Uuid(), sa.ForeignKey("subjects.id"), nullable=False),
        sa.Column("parent_id", sa.Uuid(), sa.ForeignKey("knowledge_nodes.id")),
        sa.Column("code", sa.String(length=100), nullable=False, unique=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("level", sa.Integer(), server_default="0"),
        sa.Column("description", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "questions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("subject_id", sa.Uuid(), sa.ForeignKey("subjects.id"), nullable=False),
        sa.Column("grade", sa.String(length=50)),
        sa.Column("year", sa.Integer()),
        sa.Column("school", sa.String(length=255)),
        sa.Column("question_type_id", sa.Uuid(), sa.ForeignKey("question_types.id")),
        sa.Column("score", sa.Numeric(precision=8, scale=2)),
        sa.Column("difficulty", sa.Integer()),
        sa.Column("stem", sa.Text(), nullable=False),
        sa.Column("options", postgresql.JSONB()),
        sa.Column("answer", sa.Text()),
        sa.Column("explanation", sa.Text()),
        sa.Column("source_type", sa.String(length=20), server_default="document"),
        sa.Column("source_document_name", sa.String(length=255)),
        sa.Column("status", sa.String(length=20), server_default="reviewing"),
        sa.Column("confidence", sa.Numeric(precision=4, scale=3)),
        sa.Column("occurrence_count", sa.Integer(), server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "question_images",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("question_id", sa.Uuid(), sa.ForeignKey("questions.id"), nullable=False),
        sa.Column("image_key", sa.String(length=500), nullable=False),
        sa.Column("image_type", sa.String(length=30), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("image_order", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "question_instances",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("question_id", sa.Uuid(), sa.ForeignKey("questions.id"), nullable=False),
        sa.Column("source_type", sa.String(length=20), nullable=False),
        sa.Column("source_document_name", sa.String(length=255)),
        sa.Column("source_page", sa.Integer()),
        sa.Column("source_question_number", sa.String(length=50)),
        sa.Column("year", sa.Integer()),
        sa.Column("school", sa.String(length=255)),
        sa.Column("occurrence_no", sa.Integer(), server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "question_knowledge",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("question_id", sa.Uuid(), sa.ForeignKey("questions.id"), nullable=False),
        sa.Column("knowledge_node_id", sa.Uuid(), sa.ForeignKey("knowledge_nodes.id"), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=4, scale=3)),
        sa.Column("is_primary", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "question_embeddings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("question_id", sa.Uuid(), sa.ForeignKey("questions.id"), nullable=False),
        sa.Column("embedding", Vector(2560), nullable=False),
        sa.Column("embedding_provider", sa.String(length=50), nullable=False),
        sa.Column("embedding_dimension", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "background_tasks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("task_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="queued"),
        sa.Column("progress", sa.Numeric(precision=4, scale=3)),
        sa.Column("current_stage", sa.String(length=100)),
        sa.Column("error_detail", sa.Text()),
        sa.Column("payload_json", postgresql.JSONB()),
        sa.Column("result_json", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "domain_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.Uuid()),
        sa.Column("payload_json", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "wrong_upload_tasks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("task_id", sa.Uuid(), sa.ForeignKey("background_tasks.id"), nullable=False, unique=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("image_key", sa.String(length=500), nullable=False),
        sa.Column("detected_count", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "wrong_upload_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("upload_id", sa.Uuid(), sa.ForeignKey("wrong_upload_tasks.id"), nullable=False),
        sa.Column("question_id", sa.Uuid(), sa.ForeignKey("questions.id")),
        sa.Column("content_snapshot", postgresql.JSONB()),
        sa.Column("metadata_snapshot", postgresql.JSONB()),
        sa.Column("status", sa.String(length=30), server_default="pending_review"),
        sa.Column("review_comment", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "wrong_questions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("question_id", sa.Uuid(), sa.ForeignKey("questions.id"), nullable=False),
        sa.Column("source_type", sa.String(length=20), nullable=False),
        sa.Column("error_type", sa.String(length=100)),
        sa.Column("wrong_count", sa.Integer(), server_default="1"),
        sa.Column("last_wrong_time", sa.DateTime(timezone=True)),
        sa.Column("mastery_status", sa.String(length=30), server_default="not_mastered"),
        sa.Column("review_count", sa.Integer(), server_default="0"),
        sa.Column("last_review_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "practice_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("trigger_type", sa.String(length=30), nullable=False),
        sa.Column("question_count", sa.Integer()),
        sa.Column("status", sa.String(length=30), server_default="in_progress"),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "practice_answers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("practice_sessions.id"), nullable=False),
        sa.Column("question_id", sa.Uuid(), sa.ForeignKey("questions.id"), nullable=False),
        sa.Column("question_snapshot", postgresql.JSONB()),
        sa.Column("student_answer", sa.Text()),
        sa.Column("is_correct", sa.Boolean()),
        sa.Column("duration_seconds", sa.Integer()),
        sa.Column("knowledge_point_ids", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "mastery_records",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("knowledge_node_id", sa.Uuid(), sa.ForeignKey("knowledge_nodes.id"), nullable=False),
        sa.Column("mastery_level", sa.Integer(), server_default="0"),
        sa.Column("total_attempts", sa.Integer(), server_default="0"),
        sa.Column("correct_count", sa.Integer(), server_default="0"),
        sa.Column("recent_correct_rate", sa.Numeric(precision=4, scale=3)),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "generation_jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("task_id", sa.Uuid(), sa.ForeignKey("background_tasks.id"), nullable=False, unique=True),
        sa.Column("task_type", sa.String(length=30), nullable=False),
        sa.Column("subject", sa.String(length=50)),
        sa.Column("grade", sa.String(length=50)),
        sa.Column("parameters", postgresql.JSONB()),
        sa.Column("ratio_snapshot", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "generation_results",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("generation_jobs.id"), nullable=False),
        sa.Column("question_id", sa.Uuid(), sa.ForeignKey("questions.id"), nullable=False),
        sa.Column("review_status", sa.String(length=30), server_default="pending"),
        sa.Column("review_comment", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "system_configs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("config_key", sa.String(length=100), nullable=False, unique=True),
        sa.Column("config_value", sa.Text()),
        sa.Column("description", sa.Text()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_index("ix_document_processing_logs_document_id", "document_processing_logs", ["document_id"])
    op.create_index("ix_question_types_subject_id", "question_types", ["subject_id"])
    op.create_index("ix_knowledge_nodes_subject_id", "knowledge_nodes", ["subject_id"])
    op.create_index("ix_questions_subject_grade_year", "questions", ["subject_id", "grade", "year"])
    op.create_index("ix_questions_status_confidence", "questions", ["status", "confidence"])
    op.create_index("ix_questions_source_type", "questions", ["source_type"])
    op.create_index("ix_questions_question_type_id", "questions", ["question_type_id"])
    op.create_index("ix_question_images_question_id", "question_images", ["question_id"])
    op.create_index("ix_question_instances_question_year", "question_instances", ["question_id", "year"])
    op.create_index("ix_question_knowledge_question_node", "question_knowledge", ["question_id", "knowledge_node_id"])
    op.create_index("ix_question_embeddings_question_id", "question_embeddings", ["question_id"])
    op.create_index("ix_background_tasks_type_status", "background_tasks", ["task_type", "status"])
    op.create_index("ix_domain_events_type_created", "domain_events", ["event_type", "created_at"])
    op.create_index("ix_wrong_upload_tasks_user_id", "wrong_upload_tasks", ["user_id"])
    op.create_index("ix_wrong_upload_items_upload_id", "wrong_upload_items", ["upload_id"])
    op.create_index("ix_wrong_questions_user_status", "wrong_questions", ["user_id", "mastery_status"])
    op.create_index("ix_wrong_questions_question_id", "wrong_questions", ["question_id"])
    op.create_index("ix_practice_sessions_user_id", "practice_sessions", ["user_id"])
    op.create_index("ix_practice_answers_session_question", "practice_answers", ["session_id", "question_id"])
    op.create_index("ix_mastery_records_user_knowledge", "mastery_records", ["user_id", "knowledge_node_id"])
    op.create_index("ix_generation_results_job_id", "generation_results", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_generation_results_job_id", table_name="generation_results")
    op.drop_index("ix_mastery_records_user_knowledge", table_name="mastery_records")
    op.drop_index("ix_practice_answers_session_question", table_name="practice_answers")
    op.drop_index("ix_practice_sessions_user_id", table_name="practice_sessions")
    op.drop_index("ix_wrong_questions_question_id", table_name="wrong_questions")
    op.drop_index("ix_wrong_questions_user_status", table_name="wrong_questions")
    op.drop_index("ix_wrong_upload_items_upload_id", table_name="wrong_upload_items")
    op.drop_index("ix_wrong_upload_tasks_user_id", table_name="wrong_upload_tasks")
    op.drop_index("ix_domain_events_type_created", table_name="domain_events")
    op.drop_index("ix_background_tasks_type_status", table_name="background_tasks")
    op.drop_index("ix_question_embeddings_question_id", table_name="question_embeddings")
    op.drop_index("ix_question_knowledge_question_node", table_name="question_knowledge")
    op.drop_index("ix_question_instances_question_year", table_name="question_instances")
    op.drop_index("ix_question_images_question_id", table_name="question_images")
    op.drop_index("ix_questions_question_type_id", table_name="questions")
    op.drop_index("ix_questions_source_type", table_name="questions")
    op.drop_index("ix_questions_status_confidence", table_name="questions")
    op.drop_index("ix_questions_subject_grade_year", table_name="questions")
    op.drop_index("ix_knowledge_nodes_subject_id", table_name="knowledge_nodes")
    op.drop_index("ix_question_types_subject_id", table_name="question_types")
    op.drop_index("ix_document_processing_logs_document_id", table_name="document_processing_logs")

    op.drop_table("system_configs")
    op.drop_table("generation_results")
    op.drop_table("generation_jobs")
    op.drop_table("mastery_records")
    op.drop_table("practice_answers")
    op.drop_table("practice_sessions")
    op.drop_table("wrong_questions")
    op.drop_table("wrong_upload_items")
    op.drop_table("wrong_upload_tasks")
    op.drop_table("domain_events")
    op.drop_table("background_tasks")
    op.drop_table("question_embeddings")
    op.drop_table("question_knowledge")
    op.drop_table("question_instances")
    op.drop_table("question_images")
    op.drop_table("questions")
    op.drop_table("knowledge_nodes")
    op.drop_table("question_types")
    op.drop_table("document_processing_logs")
    op.drop_table("documents")
    op.drop_table("subjects")
    op.drop_table("users")

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_column, updated_at_column, uuid_pk


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = uuid_pk()
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = uuid_pk()
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)
    object_key: Mapped[str] = mapped_column(String(500), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(50))
    grade: Mapped[str | None] = mapped_column(String(50))
    year: Mapped[int | None] = mapped_column(Integer)
    school: Mapped[str | None] = mapped_column(String(255))
    upload_status: Mapped[str] = mapped_column(String(30), default="queued")
    processing_status: Mapped[str] = mapped_column(String(30), default="pending")
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()


class DocumentProcessingLog(Base):
    __tablename__ = "document_processing_logs"

    id: Mapped[uuid.UUID] = uuid_pk()
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id"),
        index=True,
        nullable=False,
    )
    stage: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()


class QuestionType(Base):
    __tablename__ = "question_types"

    id: Mapped[uuid.UUID] = uuid_pk()
    subject_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subjects.id"),
        index=True,
        nullable=False,
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("question_types.id"))
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = created_at_column()


class KnowledgeNode(Base):
    __tablename__ = "knowledge_nodes"

    id: Mapped[uuid.UUID] = uuid_pk()
    subject_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subjects.id"),
        index=True,
        nullable=False,
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("knowledge_nodes.id"))
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = uuid_pk()
    subject_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subjects.id"),
        index=True,
        nullable=False,
    )
    grade: Mapped[str | None] = mapped_column(String(50))
    year: Mapped[int | None] = mapped_column(Integer)
    school: Mapped[str | None] = mapped_column(String(255))
    question_type_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("question_types.id"),
        index=True,
    )
    score: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    difficulty: Mapped[int | None] = mapped_column(Integer)
    stem: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[Any | None] = mapped_column(JSONB)
    answer: Mapped[str | None] = mapped_column(Text)
    explanation: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(20), default="document")
    source_document_name: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="reviewing")
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    __table_args__ = (
        Index("ix_questions_subject_grade_year", "subject_id", "grade", "year"),
        Index("ix_questions_status_confidence", "status", "confidence"),
        Index("ix_questions_source_type", "source_type"),
    )


class QuestionImage(Base):
    __tablename__ = "question_images"

    id: Mapped[uuid.UUID] = uuid_pk()
    question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("questions.id"),
        index=True,
        nullable=False,
    )
    image_key: Mapped[str] = mapped_column(String(500), nullable=False)
    image_type: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    image_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = created_at_column()


class QuestionInstance(Base):
    __tablename__ = "question_instances"

    id: Mapped[uuid.UUID] = uuid_pk()
    question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("questions.id"),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    source_document_name: Mapped[str | None] = mapped_column(String(255))
    source_page: Mapped[int | None] = mapped_column(Integer)
    source_question_number: Mapped[str | None] = mapped_column(String(50))
    year: Mapped[int | None] = mapped_column(Integer)
    school: Mapped[str | None] = mapped_column(String(255))
    occurrence_no: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = created_at_column()

    __table_args__ = (
        Index("ix_question_instances_question_year", "question_id", "year"),
    )


class QuestionKnowledge(Base):
    __tablename__ = "question_knowledge"

    id: Mapped[uuid.UUID] = uuid_pk()
    question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("questions.id"),
        nullable=False,
    )
    knowledge_node_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_nodes.id"),
        nullable=False,
    )
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = created_at_column()

    __table_args__ = (
        Index("ix_question_knowledge_question_node", "question_id", "knowledge_node_id"),
    )


class QuestionEmbedding(Base):
    __tablename__ = "question_embeddings"

    id: Mapped[uuid.UUID] = uuid_pk()
    question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("questions.id"),
        index=True,
        nullable=False,
    )
    embedding: Mapped[Any] = mapped_column(Vector(2560), nullable=False)
    embedding_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    embedding_dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = created_at_column()

class BackgroundTask(Base):
    __tablename__ = "background_tasks"

    id: Mapped[uuid.UUID] = uuid_pk()
    task_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="queued")
    progress: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    current_stage: Mapped[str | None] = mapped_column(String(100))
    error_detail: Mapped[str | None] = mapped_column(Text)
    payload_json: Mapped[Any | None] = mapped_column(JSONB)
    result_json: Mapped[Any | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    __table_args__ = (
        Index("ix_background_tasks_type_status", "task_type", "status"),
    )


class DomainEvent(Base):
    __tablename__ = "domain_events"

    id: Mapped[uuid.UUID] = uuid_pk()
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    payload_json: Mapped[Any | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = created_at_column()
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_domain_events_type_created", "event_type", "created_at"),
    )


class WrongUploadTask(Base):
    __tablename__ = "wrong_upload_tasks"

    id: Mapped[uuid.UUID] = uuid_pk()
    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("background_tasks.id"),
        unique=True,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"),
        index=True,
        nullable=False,
    )
    image_key: Mapped[str] = mapped_column(String(500), nullable=False)
    detected_count: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = created_at_column()


class WrongUploadItem(Base):
    __tablename__ = "wrong_upload_items"

    id: Mapped[uuid.UUID] = uuid_pk()
    upload_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("wrong_upload_tasks.id"),
        index=True,
        nullable=False,
    )
    question_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("questions.id"))
    content_snapshot: Mapped[Any | None] = mapped_column(JSONB)
    metadata_snapshot: Mapped[Any | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(30), default="pending_review")
    review_comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()


class WrongQuestion(Base):
    __tablename__ = "wrong_questions"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("questions.id"),
        index=True,
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    error_type: Mapped[str | None] = mapped_column(String(100))
    wrong_count: Mapped[int] = mapped_column(Integer, default=1)
    last_wrong_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    mastery_status: Mapped[str] = mapped_column(String(30), default="not_mastered")
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    last_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at_column()

    __table_args__ = (
        Index("ix_wrong_questions_user_status", "user_id", "mastery_status"),
    )


class PracticeSession(Base):
    __tablename__ = "practice_sessions"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"),
        index=True,
        nullable=False,
    )
    trigger_type: Mapped[str] = mapped_column(String(30), nullable=False)
    question_count: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30), default="in_progress")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at_column()


class PracticeAnswer(Base):
    __tablename__ = "practice_answers"

    id: Mapped[uuid.UUID] = uuid_pk()
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("practice_sessions.id"),
        nullable=False,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("questions.id"),
        nullable=False,
    )
    question_snapshot: Mapped[Any | None] = mapped_column(JSONB)
    student_answer: Mapped[str | None] = mapped_column(Text)
    is_correct: Mapped[bool | None] = mapped_column(Boolean)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    knowledge_point_ids: Mapped[Any | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = created_at_column()

    __table_args__ = (
        Index("ix_practice_answers_session_question", "session_id", "question_id"),
    )


class MasteryRecord(Base):
    __tablename__ = "mastery_records"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )
    knowledge_node_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_nodes.id"),
        nullable=False,
    )
    mastery_level: Mapped[int] = mapped_column(Integer, default=0)
    total_attempts: Mapped[int] = mapped_column(Integer, default=0)
    correct_count: Mapped[int] = mapped_column(Integer, default=0)
    recent_correct_rate: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    updated_at: Mapped[datetime] = updated_at_column()

    __table_args__ = (
        Index("ix_mastery_records_user_knowledge", "user_id", "knowledge_node_id"),
    )


class GenerationJob(Base):
    __tablename__ = "generation_jobs"

    id: Mapped[uuid.UUID] = uuid_pk()
    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("background_tasks.id"),
        unique=True,
        nullable=False,
    )
    task_type: Mapped[str] = mapped_column(String(30), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(50))
    grade: Mapped[str | None] = mapped_column(String(50))
    parameters: Mapped[Any | None] = mapped_column(JSONB)
    ratio_snapshot: Mapped[Any | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = created_at_column()
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class GenerationResult(Base):
    __tablename__ = "generation_results"

    id: Mapped[uuid.UUID] = uuid_pk()
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("generation_jobs.id"),
        index=True,
        nullable=False,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("questions.id"),
        nullable=False,
    )
    review_status: Mapped[str] = mapped_column(String(30), default="pending")
    review_comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()


class SystemConfig(Base):
    __tablename__ = "system_configs"

    id: Mapped[uuid.UUID] = uuid_pk()
    config_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    config_value: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = updated_at_column()

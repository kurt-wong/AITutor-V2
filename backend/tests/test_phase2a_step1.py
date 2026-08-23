"""
Phase 2A Step 1 验收测试。

验证 DSD 变更和入库适配的正确性：
- questions 表：移除 year/school，新增 content_hash
- question_instances 表：新增 document_id（NOT NULL），部分唯一索引
- question_knowledge 表：新增 mapping_source/review_status
- 入库逻辑：Question 不写 year/school，Instance 写 document_id
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.models import Base, Question, QuestionInstance, QuestionKnowledge
from app.models.tables import Document


# ═══════════════════════════════════════════════════════════════════
# 1. Model 字段验证
# ═══════════════════════════════════════════════════════════════════


class TestQuestionModelFields:
    """questions 表字段变更验证。"""

    def test_question_has_content_hash(self):
        """questions 表必须有 content_hash 列。"""
        cols = {c.name for c in Question.__table__.columns}
        assert "content_hash" in cols

    def test_question_no_year(self):
        """questions 表不能有 year 列。"""
        cols = {c.name for c in Question.__table__.columns}
        assert "year" not in cols

    def test_question_no_school(self):
        """questions 表不能有 school 列。"""
        cols = {c.name for c in Question.__table__.columns}
        assert "school" not in cols

    def test_question_content_hash_is_string_64(self):
        """content_hash 必须是 VARCHAR(64)。"""
        col = Question.__table__.columns["content_hash"]
        assert col.type.length == 64

    def test_question_content_hash_is_nullable(self):
        """content_hash 本步只加列，Step 5 实现 hash 逻辑，当前可为 NULL。"""
        col = Question.__table__.columns["content_hash"]
        assert col.nullable is True


class TestQuestionInstanceModelFields:
    """question_instances 表字段变更验证。"""

    def test_instance_has_document_id(self):
        """question_instances 表必须有 document_id 列。"""
        cols = {c.name for c in QuestionInstance.__table__.columns}
        assert "document_id" in cols

    def test_instance_document_id_is_not_null(self):
        """document_id 必须为 NOT NULL。"""
        col = QuestionInstance.__table__.columns["document_id"]
        assert col.nullable is False

    def test_instance_document_id_is_fk_documents(self):
        """document_id 必须是 FK documents.id。"""
        col = QuestionInstance.__table__.columns["document_id"]
        fk = list(col.foreign_keys)[0]
        assert fk.target_fullname == "documents.id"

    def test_instance_unique_index_exists(self):
        """必须有部分唯一索引 ix_question_instances_doc_qno。"""
        indexes = {idx.name for idx in QuestionInstance.__table__.indexes}
        assert "ix_question_instances_doc_qno" in indexes

    def test_instance_still_has_year(self):
        """question_instances 必须保留 year 列（从 questions 迁移过来）。"""
        cols = {c.name for c in QuestionInstance.__table__.columns}
        assert "year" in cols

    def test_instance_still_has_school(self):
        """question_instances 必须保留 school 列（从 questions 迁移过来）。"""
        cols = {c.name for c in QuestionInstance.__table__.columns}
        assert "school" in cols


class TestQuestionKnowledgeModelFields:
    """question_knowledge 表字段变更验证。"""

    def test_qk_has_mapping_source(self):
        """question_knowledge 表必须有 mapping_source 列。"""
        cols = {c.name for c in QuestionKnowledge.__table__.columns}
        assert "mapping_source" in cols

    def test_qk_has_review_status(self):
        """question_knowledge 表必须有 review_status 列。"""
        cols = {c.name for c in QuestionKnowledge.__table__.columns}
        assert "review_status" in cols

    def test_qk_review_status_default_approved(self):
        """review_status 默认值必须是 approved。"""
        # Python-side default（model 定义）
        col = QuestionKnowledge.__table__.columns["review_status"]
        assert col.default.arg == "approved"


# ═══════════════════════════════════════════════════════════════════
# 2. Ingestion 行为验证
# ═══════════════════════════════════════════════════════════════════


class TestIngestionStep1Behavior:
    """入库逻辑适配验证：Question 不写 year/school，Instance 写 document_id。"""

    def test_question_constructor_no_year_param(self):
        """Question 构造函数不应接受 year 参数。"""
        import inspect
        # Question 是 SQLAlchemy model，检查 columns 而不是 __init__
        cols = {c.name for c in Question.__table__.columns}
        assert "year" not in cols

    def test_question_constructor_no_school_param(self):
        """Question 构造函数不应接受 school 参数。"""
        cols = {c.name for c in Question.__table__.columns}
        assert "school" not in cols

    def test_question_service_create_no_year_school(self):
        """QuestionService.create_question 不应有 year/school 参数。"""
        from app.domains.question.service import QuestionService
        import inspect
        sig = inspect.signature(QuestionService.create_question)
        params = set(sig.parameters.keys())
        assert "year" not in params
        assert "school" not in params

    def test_application_service_create_no_year_school(self):
        """QuestionApplicationService.create_question 不应有 year/school 参数。"""
        from app.application.services import QuestionApplicationService
        import inspect
        sig = inspect.signature(QuestionApplicationService.create_question)
        params = set(sig.parameters.keys())
        assert "year" not in params
        assert "school" not in params


# ═══════════════════════════════════════════════════════════════════
# 3. Migration 结构验证（离线）
# ═══════════════════════════════════════════════════════════════════


class TestMigrationStructure:
    """Migration 文件结构验证（不依赖数据库连接）。"""

    def test_migration_file_exists(self):
        """migration 文件必须存在。"""
        from pathlib import Path
        migration_path = Path(__file__).parent.parent / "alembic" / "versions" / "20260821_0003_phase2a_data_foundation.py"
        assert migration_path.exists()

    def test_migration_has_upgrade(self):
        """migration 必须有 upgrade 函数。"""
        from pathlib import Path
        migration_path = Path(__file__).parent.parent / "alembic" / "versions" / "20260821_0003_phase2a_data_foundation.py"
        content = migration_path.read_text(encoding="utf-8")
        assert "def upgrade()" in content

    def test_migration_has_downgrade(self):
        """migration 必须有 downgrade 函数。"""
        from pathlib import Path
        migration_path = Path(__file__).parent.parent / "alembic" / "versions" / "20260821_0003_phase2a_data_foundation.py"
        content = migration_path.read_text(encoding="utf-8")
        assert "def downgrade()" in content

    def test_migration_uses_coalesce_for_backfill(self):
        """year/school 回填必须使用 COALESCE 避免覆盖已有值。"""
        from pathlib import Path
        migration_path = Path(__file__).parent.parent / "alembic" / "versions" / "20260821_0003_phase2a_data_foundation.py"
        content = migration_path.read_text(encoding="utf-8")
        assert "COALESCE" in content

    def test_migration_alters_document_id_not_null(self):
        """migration 必须将 document_id 设为 NOT NULL。"""
        from pathlib import Path
        migration_path = Path(__file__).parent.parent / "alembic" / "versions" / "20260821_0003_phase2a_data_foundation.py"
        content = migration_path.read_text(encoding="utf-8")
        assert "nullable=False" in content
        assert "alter_column" in content

    def test_migration_drops_questions_year(self):
        """migration 必须移除 questions.year。"""
        from pathlib import Path
        migration_path = Path(__file__).parent.parent / "alembic" / "versions" / "20260821_0003_phase2a_data_foundation.py"
        content = migration_path.read_text(encoding="utf-8")
        assert 'drop_column("questions", "year")' in content

    def test_migration_drops_questions_school(self):
        """migration 必须移除 questions.school。"""
        from pathlib import Path
        migration_path = Path(__file__).parent.parent / "alembic" / "versions" / "20260821_0003_phase2a_data_foundation.py"
        content = migration_path.read_text(encoding="utf-8")
        assert 'drop_column("questions", "school")' in content


# ═══════════════════════════════════════════════════════════════════
# 4. Index 验证
# ═══════════════════════════════════════════════════════════════════


class TestIndexDefinitions:
    """索引定义验证。"""

    def test_questions_has_subject_grade_index(self):
        """questions 必须有 ix_questions_subject_grade 索引（不含 year）。"""
        indexes = {idx.name for idx in Question.__table__.indexes}
        assert "ix_questions_subject_grade" in indexes

    def test_questions_no_subject_grade_year_index(self):
        """questions 不能有旧的 ix_questions_subject_grade_year 索引。"""
        indexes = {idx.name for idx in Question.__table__.indexes}
        assert "ix_questions_subject_grade_year" not in indexes

    def test_questions_has_content_hash_index(self):
        """questions 必须有 ix_questions_content_hash 索引。"""
        indexes = {idx.name for idx in Question.__table__.indexes}
        assert "ix_questions_content_hash" in indexes

    def test_instances_has_doc_qno_index(self):
        """question_instances 必须有 ix_question_instances_doc_qno 部分唯一索引。"""
        indexes = {idx.name for idx in QuestionInstance.__table__.indexes}
        assert "ix_question_instances_doc_qno" in indexes

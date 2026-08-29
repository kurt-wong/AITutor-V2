from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import get_document_application_service
from app.main import app


class FakeDocumentApplicationService:
    def __init__(self) -> None:
        now = datetime.now(timezone.utc)
        self.document = SimpleNamespace(
            id=uuid4(),
            filename="test.pdf",
            file_type="pdf",
            object_key="documents/abc/test.pdf",
            subject="math",
            grade="senior_high_1",
            year=2026,
            school=None,
            upload_status="queued",
            processing_status="pending",
            error_message=None,
            created_at=now,
            updated_at=now,
        )
        self.task = SimpleNamespace(
            id=uuid4(),
            task_type="document_parse",
            status="queued",
            progress=None,
            current_stage=None,
            error_detail=None,
            payload_json={"document_id": str(self.document.id)},
            result_json=None,
            created_at=now,
            updated_at=now,
        )
        self.log = SimpleNamespace(
            id=uuid4(),
            document_id=self.document.id,
            stage="upload",
            message="Document uploaded",
            created_at=now,
        )

    async def upload_document(self, **kwargs):
        return self.document, self.task

    async def list_documents(self, **kwargs):
        return [self.document], 1

    async def get_document(self, document_id):
        return self.document

    async def get_document_status(self, document_id):
        return self.document, self.task

    async def retry_document(self, document_id):
        self.task.status = "queued"
        return self.task

    async def get_document_logs(self, document_id):
        return [self.log]

    async def update_document_review(
        self,
        document_id,
        *,
        question_number,
        status,
        comment=None,
        overrides=None,
        question_id=None,
    ):
        if self.task.result_json is None:
            return None, "REVIEW_NOT_READY"
        decisions = dict(self.task.result_json.get("review_decisions") or {})
        decisions[question_number] = {
            "status": status,
            "comment": comment or "",
            "updated_at": "2026-08-17T00:00:00+00:00",
        }
        if question_id is not None:
            decisions[question_number]["question_id"] = str(question_id)
        self.task.result_json["review_decisions"] = decisions
        if overrides is not None:
            overrides_by_question = dict(self.task.result_json.get("review_overrides") or {})
            overrides_by_question[question_number] = overrides
            self.task.result_json["review_overrides"] = overrides_by_question
        return self.task, None


def _override_service(fake) -> None:
    app.dependency_overrides[get_document_application_service] = lambda: fake


def test_document_upload_and_query_endpoints() -> None:
    fake = FakeDocumentApplicationService()
    _override_service(fake)
    client = TestClient(app)

    upload_response = client.post(
        "/api/admin/documents/upload",
        files=[("files", ("test.pdf", b"pdf-content", "application/pdf"))],
        data={"subject": "math", "grade": "senior_high_1", "year": "2026"},
    )
    assert upload_response.status_code == 200
    assert upload_response.json()["data"]["document_ids"] == [str(fake.document.id)]

    list_response = client.get("/api/admin/documents")
    assert list_response.status_code == 200
    assert list_response.json()["data"]["total"] == 1

    detail_response = client.get(f"/api/admin/documents/{fake.document.id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["filename"] == "test.pdf"

    status_response = client.get(f"/api/admin/documents/{fake.document.id}/status")
    assert status_response.status_code == 200
    assert status_response.json()["data"]["status"] == "queued"

    parse_result_response = client.get(
        f"/api/admin/documents/{fake.document.id}/parse-result"
    )
    assert parse_result_response.status_code == 200
    assert parse_result_response.json()["data"]["task_id"] == str(fake.task.id)
    assert parse_result_response.json()["data"]["result"] is None

    retry_response = client.post(f"/api/admin/documents/{fake.document.id}/retry")
    assert retry_response.status_code == 200
    assert retry_response.json()["data"]["task_id"] == str(fake.task.id)

    logs_response = client.get(f"/api/admin/documents/{fake.document.id}/logs")
    assert logs_response.status_code == 200
    assert logs_response.json()["data"]["items"][0]["stage"] == "upload"

    app.dependency_overrides.clear()


def test_document_upload_rejects_unsupported_file() -> None:
    fake = FakeDocumentApplicationService()
    _override_service(fake)
    client = TestClient(app)

    response = client.post(
        "/api/admin/documents/upload",
        files=[("files", ("notes.txt", b"text", "text/plain"))],
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    app.dependency_overrides.clear()


def test_document_review_persists_decision() -> None:
    fake = FakeDocumentApplicationService()
    fake.task.result_json = {"questions": [], "status": "succeeded"}
    _override_service(fake)
    client = TestClient(app)

    response = client.put(
        f"/api/admin/documents/{fake.document.id}/review",
        json={
            "question_number": "Q1",
            "status": "approved",
            "comment": "材料与子题完整",
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["question_number"] == "Q1"
    assert data["status"] == "approved"
    assert data["comment"] == "材料与子题完整"
    assert fake.task.result_json["review_decisions"]["Q1"]["status"] == "approved"
    app.dependency_overrides.clear()


def test_document_review_requires_ready_result() -> None:
    fake = FakeDocumentApplicationService()
    _override_service(fake)
    client = TestClient(app)

    response = client.put(
        f"/api/admin/documents/{fake.document.id}/review",
        json={"question_number": "Q1", "status": "approved"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "REVIEW_NOT_READY"
    app.dependency_overrides.clear()


def test_document_review_persists_overrides() -> None:
    fake = FakeDocumentApplicationService()
    fake.task.result_json = {"questions": [], "status": "succeeded"}
    _override_service(fake)
    client = TestClient(app)

    response = client.put(
        f"/api/admin/documents/{fake.document.id}/review",
        json={
            "question_number": "Q1",
            "status": "approved",
            "overrides": {
                "stem": "修正后的题干",
                "answer": "B",
            },
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "approved"
    assert data["overrides"]["stem"] == "修正后的题干"
    assert data["overrides"]["answer"] == "B"
    assert fake.task.result_json["review_overrides"]["Q1"]["answer"] == "B"
    app.dependency_overrides.clear()


def test_document_review_rejects_non_object_overrides() -> None:
    fake = FakeDocumentApplicationService()
    fake.task.result_json = {"questions": [], "status": "succeeded"}
    _override_service(fake)
    client = TestClient(app)

    response = client.put(
        f"/api/admin/documents/{fake.document.id}/review",
        json={
            "question_number": "Q1",
            "status": "approved",
            "overrides": "not-an-object",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    app.dependency_overrides.clear()


def test_admin_api_rejects_request_without_key_when_auth_enabled():
    """When admin_api_key is not the dev default, missing X-API-Key returns 401."""
    from app.core.config import settings

    original_key = settings.admin_api_key
    settings.admin_api_key = "real-secret-key"
    try:
        client = TestClient(app)
        response = client.get("/api/admin/documents")
        assert response.status_code == 401
        assert "Invalid or missing API key" in response.json()["detail"]
    finally:
        settings.admin_api_key = original_key


def test_admin_api_accepts_valid_key():
    """When admin_api_key is set, valid X-API-Key passes auth."""
    from app.core.config import settings

    original_key = settings.admin_api_key
    settings.admin_api_key = "real-secret-key"
    try:
        fake = FakeDocumentApplicationService()
        _override_service(fake)
        client = TestClient(app)
        response = client.get(
            "/api/admin/documents",
            headers={"X-API-Key": "real-secret-key"},
        )
        assert response.status_code == 200
    finally:
        settings.admin_api_key = original_key
        app.dependency_overrides.clear()

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

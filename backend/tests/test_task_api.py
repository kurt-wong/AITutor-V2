from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import get_task_application_service
from app.main import app


class FakeTaskApplicationService:
    def __init__(self) -> None:
        now = datetime.now(timezone.utc)
        self.task = SimpleNamespace(
            id=uuid4(),
            task_type="document_parse",
            status="failed",
            progress=None,
            current_stage=None,
            error_detail="parse failed",
            payload_json={"document_id": str(uuid4())},
            result_json=None,
            created_at=now,
            updated_at=now,
        )

    async def list_tasks(self, **kwargs):
        return [self.task], 1

    async def get_task(self, task_id):
        return self.task

    async def retry_task(self, task_id):
        self.task.status = "queued"
        return self.task


def test_task_endpoints() -> None:
    fake = FakeTaskApplicationService()
    app.dependency_overrides[get_task_application_service] = lambda: fake
    client = TestClient(app)

    list_response = client.get("/api/tasks")
    assert list_response.status_code == 200
    assert list_response.json()["data"]["total"] == 1

    detail_response = client.get(f"/api/tasks/{fake.task.id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["task_type"] == "document_parse"

    retry_response = client.post(f"/api/tasks/{fake.task.id}/retry")
    assert retry_response.status_code == 200
    assert retry_response.json()["data"]["status"] == "queued"

    app.dependency_overrides.clear()


def test_task_retry_rejects_non_failed_task() -> None:
    fake = FakeTaskApplicationService()
    fake.task.status = "queued"
    app.dependency_overrides[get_task_application_service] = lambda: fake
    client = TestClient(app)

    response = client.post(f"/api/tasks/{fake.task.id}/retry")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "TASK_RETRY_INVALID"
    app.dependency_overrides.clear()

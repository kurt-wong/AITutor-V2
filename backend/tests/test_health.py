from fastapi.testclient import TestClient

from app.api.routes import health
from app.main import app

client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["status"] == "ok"
    assert payload["meta"]["request_id"] != "-"
    assert isinstance(payload["meta"]["latency_ms"], int)
    assert response.headers["X-Request-ID"] == payload["meta"]["request_id"]


def test_dependency_health_check() -> None:
    async def fake_postgresql() -> dict:
        return {"status": "ok", "message": None}

    async def fake_redis() -> dict:
        return {"status": "ok", "message": None}

    async def fake_minio() -> dict:
        return {"status": "ok", "message": None}

    health._check_postgresql = fake_postgresql
    health._check_redis = fake_redis
    health._check_minio = fake_minio

    response = TestClient(app).get("/api/health/dependencies")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["status"] == "ok"
    assert set(payload["dependencies"]) == {"postgresql", "redis", "minio"}

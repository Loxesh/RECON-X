
from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "recon-x-api",
        "api_version": "v1",
    }


def test_readiness_endpoint_when_database_is_unavailable():
    with TestClient(app) as client:
        app.state.mongodb_healthy = False

        response = client.get("/api/v1/ready")

    assert response.status_code == 503

    body = response.json()

    assert body["success"] is False
    assert body["error"]["code"] == "HTTP_503"
    assert body["error"]["message"]
    assert body["request_id"]
    assert "detail" not in body

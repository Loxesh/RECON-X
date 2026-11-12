
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/v1/health")

    assert response.status_code == 200

    assert response.json() == {
        "status": "healthy",
        "service": "recon-x-api",
        "api_version": "v1",
    }

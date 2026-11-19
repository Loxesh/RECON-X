
import logging

import pytest

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.exceptions import register_exception_handlers
from app.core.middleware import RequestContextMiddleware


@pytest.fixture
def client():
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)
    register_exception_handlers(app)

    @app.get("/health")
    def health():
        return {"status": "healthy"}

    @app.get("/items/{item_id}")
    def get_item(item_id: int):
        return {"item_id": item_id}

    @app.get("/expected-error")
    def expected_error():
        raise HTTPException(
            status_code=403,
            detail="Access denied.",
        )

    @app.get("/unexpected-error")
    def unexpected_error():
        raise RuntimeError("Sensitive internal database detail")

    return TestClient(app, raise_server_exceptions=False)


def test_request_id_is_generated(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers.get("X-Request-ID")


def test_incoming_request_id_is_preserved(client):
    response = client.get(
        "/health",
        headers={"X-Request-ID": "recon-test-123"},
    )

    assert response.headers["X-Request-ID"] == "recon-test-123"


def test_invalid_request_id_is_replaced(client):
    response = client.get(
        "/health",
        headers={"X-Request-ID": "bad request id"},
    )

    assert response.headers["X-Request-ID"] != "bad request id"


def test_validation_error_uses_standard_envelope(client):
    response = client.get("/items/not-a-number")

    assert response.status_code == 422

    body = response.json()

    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["request_id"] == response.headers["X-Request-ID"]
    assert body["error"]["details"]


def test_http_error_uses_standard_envelope(client):
    response = client.get("/expected-error")

    assert response.status_code == 403
    assert response.json()["success"] is False
    assert response.json()["error"]["message"] == "Access denied."


def test_internal_error_does_not_leak_details(client):
    response = client.get("/unexpected-error")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert "Sensitive internal database detail" not in response.text


def test_request_id_is_present_on_error(client):
    response = client.get("/expected-error")

    assert response.headers.get("X-Request-ID")
    assert (
        response.json()["request_id"]
        == response.headers["X-Request-ID"]
    )


def test_request_logging_is_emitted(client, caplog):
    with caplog.at_level(logging.INFO, logger="recon_x.api"):
        client.get("/health")

    assert "API request completed" in caplog.text

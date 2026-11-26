
"""API-level tests for the human review endpoints."""

from datetime import datetime, timezone

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from app.api.deps.auth_deps import get_current_user
from app.api.v1.routers import reviews as reviews_router
from app.main import app


ORG_ID = "REVIEW-API-TEST"
REVIEWER_ID = ObjectId()
EXCEPTION_ID = str(ObjectId())
NOW = datetime.now(timezone.utc)


class StubReviewService:
    """Controlled service stub for HTTP contract tests."""

    instances = []

    def __init__(self, database, org_id):
        self.database = database
        self.org_id = org_id
        self.instances.append(self)

    def list_queue(self, *, skip=0, limit=50):
        return [
            {
                "id": EXCEPTION_ID,
                "job_id": "JOB-API-001",
                "type": "AMOUNT_MISMATCH",
                "severity": "HIGH",
                "summary": "Transaction amount mismatch",
                "status": "OPEN",
                "review_required": True,
                "created_at": NOW,
            }
        ]

    def get_review(self, exception_id):
        return {
            "id": exception_id,
            "job_id": "JOB-API-001",
            "type": "AMOUNT_MISMATCH",
            "severity": "HIGH",
            "summary": "Transaction amount mismatch",
            "primary_txn_ids": [],
            "related_match_ids": [],
            "status": "OPEN",
            "review_required": True,
            "risk": {},
            "evidence": {},
            "investigation_id": None,
            "assigned_to": None,
            "created_at": NOW,
        }

    def decide(self, **kwargs):
        self.last_decision = kwargs

        return {
            "id": str(ObjectId()),
            "exception_id": kwargs["exception_id"],
            "job_id": "JOB-API-001",
            "decision": kwargs["decision"],
            "reviewer_id": kwargs["reviewer_id"],
            "reviewer_role": "finance_analyst",
            "comment": kwargs["comment"],
            "before": {
                "status": "OPEN",
                "review_required": True,
            },
            "after": kwargs["after"] or {},
            "decided_at": NOW,
            "replayed": False,
        }


@pytest.fixture
def api_client(monkeypatch):
    """Create an HTTP test client without starting MongoDB lifespan."""

    original_overrides = app.dependency_overrides.copy()
    original_database = getattr(
        app.state,
        "mongodb_database",
        None,
    )

    app.state.mongodb_database = object()
    app.dependency_overrides.clear()

    StubReviewService.instances.clear()

    monkeypatch.setattr(
        reviews_router,
        "ReviewService",
        StubReviewService,
    )

    client = TestClient(app)

    yield client

    client.close()
    app.dependency_overrides.clear()
    app.dependency_overrides.update(original_overrides)

    app.state.mongodb_database = original_database


def authenticate_as(client, role):
    """Override authentication with a controlled user."""

    user = {
        "_id": REVIEWER_ID,
        "org_id": ORG_ID,
        "roles": [role],
        "status": "ACTIVE",
    }

    app.dependency_overrides[get_current_user] = lambda: user


def test_review_queue_requires_authentication(api_client):
    response = api_client.get("/api/v1/reviews")

    assert response.status_code == 401


def test_review_detail_requires_authentication(api_client):
    response = api_client.get(
        f"/api/v1/reviews/{EXCEPTION_ID}"
    )

    assert response.status_code == 401


def test_review_decision_requires_authentication(api_client):
    response = api_client.post(
        f"/api/v1/reviews/{EXCEPTION_ID}/decision",
        json={"decision": "approve"},
        headers={"Idempotency-Key": "api-test-001"},
    )

    assert response.status_code == 401


def test_auditor_can_read_review_queue(api_client):
    authenticate_as(api_client, "auditor")

    response = api_client.get("/api/v1/reviews")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == EXCEPTION_ID


def test_auditor_can_read_review_details(api_client):
    authenticate_as(api_client, "auditor")

    response = api_client.get(
        f"/api/v1/reviews/{EXCEPTION_ID}"
    )

    assert response.status_code == 200
    assert response.json()["id"] == EXCEPTION_ID
    assert response.json()["status"] == "OPEN"


def test_auditor_cannot_submit_review_decision(api_client):
    authenticate_as(api_client, "auditor")

    response = api_client.post(
        f"/api/v1/reviews/{EXCEPTION_ID}/decision",
        json={"decision": "approve"},
        headers={"Idempotency-Key": "api-test-002"},
    )

    assert response.status_code == 403


def test_finance_analyst_can_submit_review_decision(api_client):
    authenticate_as(api_client, "finance_analyst")

    response = api_client.post(
        f"/api/v1/reviews/{EXCEPTION_ID}/decision",
        json={
            "decision": "approve",
            "comment": "Evidence reviewed.",
        },
        headers={"Idempotency-Key": "api-test-003"},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["exception_id"] == EXCEPTION_ID
    assert body["decision"] == "approve"
    assert body["reviewer_role"] == "finance_analyst"
    assert body["replayed"] is False


def test_decision_requires_idempotency_key(api_client):
    authenticate_as(api_client, "finance_analyst")

    response = api_client.post(
        f"/api/v1/reviews/{EXCEPTION_ID}/decision",
        json={"decision": "approve"},
    )

    assert response.status_code == 422


def test_decision_rejects_unexpected_request_fields(api_client):
    authenticate_as(api_client, "finance_analyst")

    response = api_client.post(
        f"/api/v1/reviews/{EXCEPTION_ID}/decision",
        json={
            "decision": "approve",
            "unexpected_field": "not allowed",
        },
        headers={"Idempotency-Key": "api-test-004"},
    )

    assert response.status_code == 422


def test_decision_rejects_invalid_decision_value(api_client):
    authenticate_as(api_client, "finance_analyst")

    response = api_client.post(
        f"/api/v1/reviews/{EXCEPTION_ID}/decision",
        json={"decision": "cancel"},
        headers={"Idempotency-Key": "api-test-005"},
    )

    assert response.status_code == 422


def test_review_queue_validates_pagination(api_client):
    authenticate_as(api_client, "auditor")

    response = api_client.get(
        "/api/v1/reviews?skip=-1"
    )

    assert response.status_code == 422

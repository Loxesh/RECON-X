
"""Integration tests for the RECON X human review workflow."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from bson import ObjectId
from fastapi import HTTPException

from app.core.config import settings
from app.core.database import create_mongo_client
from app.governance.audit_repository import AuditChainError
from app.models.enums import ApprovalDecision
from app.services.review_service import ReviewService


@pytest.fixture
def review_context():
    """Create isolated MongoDB records for each review test."""

    client = create_mongo_client()
    database = client[settings.mongodb_database]

    org_id = f"REVIEW-TEST-{uuid4().hex}"
    exception_id = None

    try:
        exception_id = database["exceptions"].insert_one(
            {
                "org_id": org_id,
                "job_id": f"JOB-{uuid4().hex}",
                "type": "AMOUNT_MISMATCH",
                "severity": "HIGH",
                "summary": "Review workflow integration test",
                "primary_txn_ids": [],
                "related_match_ids": [],
                "status": "OPEN",
                "review_required": True,
                "risk": {},
                "evidence": {},
                "investigation_id": None,
                "assigned_to": None,
                "status_history": [],
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "schema_version": 1,
            }
        ).inserted_id

        yield {
            "client": client,
            "database": database,
            "org_id": org_id,
            "exception_id": str(exception_id),
            "service": ReviewService(database, org_id),
        }

    finally:
        if exception_id is not None:
            database["exceptions"].delete_many(
                {
                    "_id": exception_id,
                    "org_id": org_id,
                }
            )

        database["approvals"].delete_many({"org_id": org_id})
        database["audit_events"].delete_many({"org_id": org_id})
        client.close()


def submit_decision(
    context,
    *,
    decision=ApprovalDecision.APPROVE,
    reviewer_roles=None,
    idempotency_key=None,
    comment=None,
    after=None,
):
    """Submit a decision using the real review service."""

    return context["service"].decide(
        exception_id=context["exception_id"],
        decision=decision,
        reviewer_id="REVIEWER-TEST-001",
        reviewer_roles=reviewer_roles or ["finance_analyst"],
        idempotency_key=idempotency_key or uuid4().hex,
        comment=comment,
        after=after or {},
        correlation_id=f"CORR-{uuid4().hex}",
    )


def get_exception(context):
    return context["database"]["exceptions"].find_one(
        {"_id": ObjectId(context["exception_id"])}
    )


def count_approvals(context):
    return context["database"]["approvals"].count_documents(
        {"org_id": context["org_id"]}
    )


def count_review_audits(context):
    return context["database"]["audit_events"].count_documents(
        {
            "org_id": context["org_id"],
            "event_type": "HUMAN_REVIEW_DECISION",
        }
    )


def test_auditor_cannot_decide_review(review_context):
    """Auditors must not be able to submit approval decisions."""

    with pytest.raises(HTTPException) as exc_info:
        submit_decision(
            review_context,
            reviewer_roles=["auditor"],
        )

    assert exc_info.value.status_code == 403
    assert count_approvals(review_context) == 0
    assert get_exception(review_context)["review_required"] is True


def test_authorized_reviewer_can_approve(review_context):
    """An authorized finance analyst can approve an open review."""

    result = submit_decision(
        review_context,
        decision=ApprovalDecision.APPROVE,
        idempotency_key="approve-test-001",
        comment="Verified supporting evidence.",
    )

    assert result["decision"] == ApprovalDecision.APPROVE.value
    assert result["reviewer_role"] == "finance_analyst"
    assert result.get("replayed", False) is False

    exception = get_exception(review_context)

    assert exception["status"] == "APPROVED"
    assert exception["review_required"] is False
    assert len(exception["status_history"]) == 1
    assert exception["status_history"][0]["status"] == "APPROVED"
    assert exception["status_history"][0]["changed_by"] == "REVIEWER-TEST-001"

    assert count_approvals(review_context) == 1
    assert count_review_audits(review_context) == 1


def test_authorized_reviewer_can_reject(review_context):
    """A reject decision transitions the exception to REJECTED."""

    result = submit_decision(
        review_context,
        decision=ApprovalDecision.REJECT,
        idempotency_key="reject-test-001",
        comment="Evidence does not support the exception.",
    )

    assert result["decision"] == ApprovalDecision.REJECT.value

    exception = get_exception(review_context)

    assert exception["status"] == "REJECTED"
    assert exception["review_required"] is False
    assert len(exception["status_history"]) == 1
    assert exception["status_history"][0]["status"] == "REJECTED"
    assert exception["status_history"][0]["comment"] == (
        "Evidence does not support the exception."
    )

    assert count_approvals(review_context) == 1
    assert count_review_audits(review_context) == 1


def test_identical_idempotent_request_returns_original_decision(review_context):
    """An identical retry must return the original approval record."""

    key = "approve-replay-001"

    first = submit_decision(
        review_context,
        decision=ApprovalDecision.APPROVE,
        idempotency_key=key,
        comment="Verified.",
    )

    second = submit_decision(
        review_context,
        decision=ApprovalDecision.APPROVE,
        idempotency_key=key,
        comment="Verified.",
    )

    assert first["id"] == second["id"]
    assert first["decision"] == second["decision"]
    assert second["replayed"] is True

    assert count_approvals(review_context) == 1
    assert count_review_audits(review_context) == 1


def test_same_idempotency_key_with_different_payload_is_rejected(
    review_context,
):
    """A key cannot be reused for a different decision request."""

    key = "approve-conflict-001"

    submit_decision(
        review_context,
        decision=ApprovalDecision.APPROVE,
        idempotency_key=key,
        comment="Original request.",
    )

    with pytest.raises(HTTPException) as exc_info:
        submit_decision(
            review_context,
            decision=ApprovalDecision.REJECT,
            idempotency_key=key,
            comment="Different request.",
        )

    assert exc_info.value.status_code == 409
    assert count_approvals(review_context) == 1


def test_modify_requires_non_empty_proposal(review_context):
    """A modify decision must include a non-empty proposal."""

    with pytest.raises(HTTPException) as exc_info:
        submit_decision(
            review_context,
            decision=ApprovalDecision.MODIFY,
            idempotency_key="modify-empty-001",
            after={},
        )

    assert exc_info.value.status_code == 422
    assert get_exception(review_context)["review_required"] is True
    assert count_approvals(review_context) == 0


def test_modify_stores_proposal_and_keeps_review_open(review_context):
    """Modification proposals are stored without closing the review."""

    proposal = {
        "proposed_amount": "1250.00",
        "reason": "Supporting evidence indicates a corrected amount.",
    }

    result = submit_decision(
        review_context,
        decision=ApprovalDecision.MODIFY,
        idempotency_key="modify-valid-001",
        after=proposal,
    )

    assert result["decision"] == ApprovalDecision.MODIFY.value
    assert result["after"] == proposal
    assert result["policy_snapshot"]["exception_status_after"] == "OPEN"
    assert result["policy_snapshot"]["review_required_after"] is True

    exception = get_exception(review_context)

    assert exception["status"] == "OPEN"
    assert exception["review_required"] is True
    assert exception["status_history"] == []
    assert "proposed_amount" not in exception

    queued_ids = {
        item["id"]
        for item in review_context["service"].list_queue()
    }

    assert review_context["exception_id"] in queued_ids
    assert count_approvals(review_context) == 1
    assert count_review_audits(review_context) == 1


def test_review_can_be_decided_after_modify_proposal(review_context):
    """A later decision can close a review after a modify proposal."""

    proposal = {
        "proposed_amount": "1250.00",
        "reason": "Corrected amount proposed.",
    }

    submit_decision(
        review_context,
        decision=ApprovalDecision.MODIFY,
        idempotency_key="modify-then-approve-001",
        after=proposal,
    )

    result = submit_decision(
        review_context,
        decision=ApprovalDecision.APPROVE,
        idempotency_key="approve-after-modify-001",
        comment="Proposal reviewed and approved.",
    )

    assert result["decision"] == ApprovalDecision.APPROVE.value

    exception = get_exception(review_context)

    assert exception["status"] == "APPROVED"
    assert exception["review_required"] is False
    assert [item["status"] for item in exception["status_history"]] == [
        "APPROVED"
    ]

    assert count_approvals(review_context) == 2
    assert count_review_audits(review_context) == 2


def test_failed_audit_write_rolls_back_review_decision(
    review_context,
    monkeypatch,
):
    """Unexpected audit errors must roll back the transaction."""

    def fail_audit(*args, **kwargs):
        raise RuntimeError("Simulated audit write failure")

    monkeypatch.setattr(
        review_context["service"].audit_logger,
        "log",
        fail_audit,
    )

    with pytest.raises(RuntimeError):
        submit_decision(
            review_context,
            idempotency_key="audit-rollback-001",
        )

    exception = get_exception(review_context)

    assert exception["status"] == "OPEN"
    assert exception["review_required"] is True
    assert exception["status_history"] == []
    assert count_approvals(review_context) == 0
    assert count_review_audits(review_context) == 0


def test_audit_chain_error_returns_503_and_rolls_back(
    review_context,
    monkeypatch,
):
    """Audit-chain failures must return 503 and roll back all writes."""

    def fail_audit(*args, **kwargs):
        raise AuditChainError("Simulated audit chain failure")

    monkeypatch.setattr(
        review_context["service"].audit_logger,
        "log",
        fail_audit,
    )

    with pytest.raises(HTTPException) as exc_info:
        submit_decision(
            review_context,
            idempotency_key="audit-chain-rollback-001",
        )

    assert exc_info.value.status_code == 503

    exception = get_exception(review_context)

    assert exception["status"] == "OPEN"
    assert exception["review_required"] is True
    assert exception["status_history"] == []
    assert count_approvals(review_context) == 0
    assert count_review_audits(review_context) == 0


def test_competing_decisions_cannot_both_succeed(review_context):
    """Only one of two competing decisions can be committed."""

    def decide(decision_number):
        try:
            return submit_decision(
                review_context,
                decision=ApprovalDecision.APPROVE,
                idempotency_key=f"concurrent-{decision_number}",
            )
        except HTTPException as exc:
            return exc.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(decide, [1, 2]))

    successes = [
        result for result in results
        if isinstance(result, dict)
    ]

    failures = [
        result for result in results
        if isinstance(result, int)
    ]

    assert len(successes) == 1
    assert len(failures) == 1
    assert failures[0] in {409, 503}

    exception = get_exception(review_context)

    assert exception["status"] == "APPROVED"
    assert exception["review_required"] is False
    assert len(exception["status_history"]) == 1

    assert count_approvals(review_context) == 1
    assert count_review_audits(review_context) == 1


"""Integration tests for transactional audit hash chains."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.core.config import settings
from app.core.database import create_mongo_client
from app.governance import AuditLogger, AuditRepository


@pytest.fixture
def audit_repository():
    client = create_mongo_client()
    database = client[settings.mongodb_database]
    org_id = f"AUDIT-TEST-{uuid4().hex}"

    repository = AuditRepository(database, org_id)

    try:
        yield repository
    finally:
        database["audit_events"].delete_many({"org_id": org_id})
        client.close()


def make_event(index: int) -> dict:
    return {
        "event_type": "AUDIT_TEST",
        "actor": {
            "actor_id": f"TEST-{index}",
            "actor_type": "SYSTEM",
            "name": "Audit test",
        },
        "resource": {
            "resource_type": "TEST",
            "resource_id": f"RESOURCE-{index}",
        },
        "action": "CREATE",
        "outcome": "SUCCESS",
        "details": {"index": index},
        "correlation_id": f"CORR-{index}",
        "ts": datetime.now(timezone.utc),
    }


def test_audit_append_and_verify(audit_repository):
    logger = AuditLogger(audit_repository)
    event = make_event(1)

    result = logger.log(
        event_type=event["event_type"],
        actor=event["actor"],
        resource=event["resource"],
        action=event["action"],
        outcome=event["outcome"],
        correlation_id=event["correlation_id"],
        details=event["details"],
        timestamp=event["ts"],
    )

    assert result["seq"] == 1
    assert result["prev_hash"] is None
    assert len(result["hash"]) == 64

    verification = logger.verify()

    assert verification["valid"] is True
    assert verification["verified_events"] == 1


def test_concurrent_appends_have_unique_sequences(audit_repository):
    total_events = 20

    def append_event(index):
        return audit_repository.append(make_event(index))

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(
            executor.map(append_event, range(total_events))
        )

    sequences = sorted(
        result["seq"] for result in results
    )

    assert sequences == list(range(1, total_events + 1))

    verification = audit_repository.verify_chain()

    assert verification["valid"] is True
    assert verification["verified_events"] == total_events


def test_tampering_is_detected(audit_repository):
    audit_repository.append(make_event(1))
    audit_repository.append(make_event(2))

    audit_repository.collection.update_one(
        {
            "org_id": audit_repository.org_id,
            "seq": 1,
        },
        {
            "$set": {
                "details.index": 999,
            }
        },
    )

    verification = audit_repository.verify_chain()

    assert verification["valid"] is False
    assert verification["failed_sequence"] == 1


def test_chain_detects_previous_hash_tampering(audit_repository):
    audit_repository.append(make_event(1))
    audit_repository.append(make_event(2))

    audit_repository.collection.update_one(
        {
            "org_id": audit_repository.org_id,
            "seq": 2,
        },
        {
            "$set": {
                "prev_hash": "tampered-hash",
            }
        },
    )

    verification = audit_repository.verify_chain()

    assert verification["valid"] is False
    assert verification["failed_sequence"] == 2

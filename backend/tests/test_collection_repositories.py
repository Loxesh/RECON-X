
from unittest.mock import MagicMock

import pytest

from app.repositories import (
    AgentExecutionRepository,
    ApprovalRepository,
    AuditEventRepository,
    ExceptionRepository,
    IngestionJobRepository,
    InvestigationRepository,
    LLMUsageRepository,
    MatchResultRepository,
    OrganizationRepository,
    ReconciliationJobRepository,
    ReportRepository,
    TransactionRepository,
    UploadedFileRepository,
    UserRepository,
    WorkflowRunRepository,
)


@pytest.fixture
def mock_database():
    """Provide a mock database with separate mock collections."""

    collections = {}

    database = MagicMock()

    def get_collection(name):
        if name not in collections:
            collections[name] = MagicMock(name=f"{name}_collection")
        return collections[name]

    database.__getitem__.side_effect = get_collection
    database._test_collections = collections

    return database


@pytest.mark.parametrize(
    ("repository_class", "collection_name"),
    [
        (UserRepository, "users"),
        (UploadedFileRepository, "uploaded_files"),
        (IngestionJobRepository, "ingestion_jobs"),
        (TransactionRepository, "transactions"),
        (ReconciliationJobRepository, "reconciliation_jobs"),
        (MatchResultRepository, "match_results"),
        (ExceptionRepository, "exceptions"),
        (InvestigationRepository, "investigations"),
        (AgentExecutionRepository, "agent_executions"),
        (WorkflowRunRepository, "workflow_runs"),
        (ApprovalRepository, "approvals"),
        (ReportRepository, "reports"),
        (LLMUsageRepository, "llm_usage"),
    ],
)
def test_tenant_repository_uses_correct_collection(
    mock_database,
    repository_class,
    collection_name,
):
    repository = repository_class(mock_database, "ORG-001")

    assert repository.collection is mock_database[collection_name]
    assert repository.org_id == "ORG-001"


def test_tenant_repositories_reject_missing_org_id(mock_database):
    with pytest.raises(ValueError):
        UserRepository(mock_database, "")

    with pytest.raises(ValueError):
        AuditEventRepository(mock_database, "   ")


def test_organization_repository_uses_organizations_collection(
    mock_database,
):
    repository = OrganizationRepository(mock_database)

    assert repository.collection is mock_database["organizations"]


def test_organization_lookup_uses_slug(mock_database):
    repository = OrganizationRepository(mock_database)
    expected = {"slug": "acme-finance"}

    repository.collection.find_one.return_value = expected

    result = repository.get_by_slug("acme-finance")

    assert result == expected
    repository.collection.find_one.assert_called_once_with(
        {"slug": "acme-finance"}
    )


def test_organization_lookup_rejects_blank_slug(mock_database):
    repository = OrganizationRepository(mock_database)

    assert repository.get_by_slug("") is None
    repository.collection.find_one.assert_not_called()


def test_audit_append_injects_trusted_org_id(mock_database):
    repository = AuditEventRepository(mock_database, "ORG-001")

    repository.collection.insert_one.return_value.inserted_id = "mock-id"

    result = repository.append(
        {
            "seq": 1,
            "event_type": "TEST_EVENT",
            "hash": "test-hash",
        }
    )

    inserted_document = repository.collection.insert_one.call_args.args[0]

    assert inserted_document["org_id"] == "ORG-001"
    assert inserted_document["seq"] == 1
    assert result["_id"] == "mock-id"


def test_audit_append_rejects_different_tenant(mock_database):
    repository = AuditEventRepository(mock_database, "ORG-001")

    with pytest.raises(ValueError):
        repository.append(
            {
                "org_id": "ORG-002",
                "seq": 1,
                "event_type": "TEST_EVENT",
                "hash": "test-hash",
            }
        )

    repository.collection.insert_one.assert_not_called()


def test_audit_list_always_scopes_to_tenant(mock_database):
    repository = AuditEventRepository(mock_database, "ORG-001")

    cursor = MagicMock()
    cursor.skip.return_value.limit.return_value = []
    repository.collection.find.return_value.sort.return_value = cursor

    repository.list({"event_type": "TEST_EVENT"})

    query = repository.collection.find.call_args.args[0]

    assert query == {
        "$and": [
            {"org_id": "ORG-001"},
            {"event_type": "TEST_EVENT"},
        ]
    }

    repository.collection.find.return_value.sort.assert_called_once_with(
        [("seq", 1)]
    )


def test_audit_repository_has_no_update_or_delete_methods(mock_database):
    repository = AuditEventRepository(mock_database, "ORG-001")

    assert not hasattr(repository, "update_by_id")
    assert not hasattr(repository, "delete_by_id")


def test_audit_count_always_scopes_to_tenant(mock_database):
    repository = AuditEventRepository(mock_database, "ORG-001")

    repository.collection.count_documents.return_value = 3

    result = repository.count({"event_type": "TEST_EVENT"})

    assert result == 3
    repository.collection.count_documents.assert_called_once_with(
        {
            "$and": [
                {"org_id": "ORG-001"},
                {"event_type": "TEST_EVENT"},
            ]
        }
    )

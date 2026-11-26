
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from bson.decimal128 import Decimal128
from pydantic import TypeAdapter, ValidationError

from app.models.base import DocumentBase, TenantDocument
from app.models.bson import (
    Money,
    from_bson_value,
    model_to_bson_document,
    to_bson_value,
)
from app.models.enums import (
    ApprovalDecision,
    AuditOutcome,
    ConfidenceLabel,
    MatchOrigin,
    MatchType,
    SourceType,
    TransactionDirection,
    TransactionValidity,
)

from app.models.organization import OrganizationDocument
from app.models.user import UserDocument
from app.models.uploaded_file import UploadedFileDocument, FilePeriod
from app.models.ingestion_job import IngestionJobDocument
from app.models.transaction import TransactionDocument
from app.models.reconciliation_job import ReconciliationJobDocument
from app.models.match_result import MatchResultDocument
from app.models.exception import ExceptionDocument
from app.models.investigation import InvestigationDocument
from app.models.agent_execution import AgentExecutionDocument
from app.models.workflow_run import WorkflowRunDocument
from app.models.approval import ApprovalDocument
from app.models.audit_event import AuditEventDocument
from app.models.report import ReportDocument
from app.models.llm_usage import LLMUsageDocument


NOW = datetime.now(timezone.utc)
SHA256 = "a" * 64


# --------------------------------------------------
# Sample documents for all 15 collections
# --------------------------------------------------

SAMPLE_DOCUMENTS = {
    OrganizationDocument: {
        "name": "Sample Organization",
        "slug": "sample-organization",
    },

    UserDocument: {
        "org_id": "ORG001",
        "email": "user@example.com",
    },

    UploadedFileDocument: {
        "org_id": "ORG001",
        "source_type": SourceType.BANK,
        "original_filename": "bank_statement.csv",
        "content_type": "text/csv",
        "size_bytes": 1024,
        "sha256": SHA256,
        "storage_bucket": "recon-x",
        "storage_key": "uploads/bank_statement.csv",
        "uploaded_by": "USER001",
        "period": {
            "start_date": date(2026, 1, 1),
            "end_date": date(2026, 1, 31),
        },
    },

    IngestionJobDocument: {
        "org_id": "ORG001",
        "file_id": "FILE001",
    },

    TransactionDocument: {
        "org_id": "ORG001",
        "job_id": "JOB001",
        "file_id": "FILE001",
        "source_type": SourceType.BANK,
        "source_row": 1,
        "txn_date": NOW,
        "amount": Decimal("7500.50"),
        "currency": "INR",
        "direction": TransactionDirection.CREDIT,
        "fingerprint": "TXN-FINGERPRINT-001",
    },

    ReconciliationJobDocument: {
        "org_id": "ORG001",
        "name": "January Reconciliation",
        "period": {
            "start_date": NOW,
            "end_date": NOW,
        },
        "idempotency_key": "IDEMPOTENCY001",
        "file_ids": {
            "bank": "FILE001",
            "ledger": "FILE002",
        },
        "created_by": "USER001",
    },

    MatchResultDocument: {
        "org_id": "ORG001",
        "job_id": "JOB001",
        "relationship": {
            "side_a": "BANK",
            "side_b": "LEDGER",
        },
        "match_type": MatchType.EXACT,
        "origin": MatchOrigin.DETERMINISTIC_DECISION,
        "side_a_ids": ["TXN001"],
        "side_b_ids": ["TXN002"],
        "amount_a": Decimal("7500.50"),
        "amount_b": Decimal("7500.50"),
        "difference": Decimal("0.00"),
        "score": 100,
        "confidence": ConfidenceLabel.HIGH,
    },

    ExceptionDocument: {
        "org_id": "ORG001",
        "job_id": "JOB001",
        "type": "AMOUNT_MISMATCH",
        "severity": "HIGH",
        "summary": "Transaction amounts do not match.",
    },

    InvestigationDocument: {
        "org_id": "ORG001",
        "exception_id": "EXCEPTION001",
        "confidence_label": ConfidenceLabel.HIGH,
        "generated_by": {
            "agent": "investigation_agent",
        },
    },

    AgentExecutionDocument: {
        "org_id": "ORG001",
        "job_id": "JOB001",
        "workflow_run_id": "WORKFLOW001",
        "agent_name": "matching_agent",
        "step": "transaction_matching",
        "input_hash": "INPUT001",
    },

    WorkflowRunDocument: {
        "org_id": "ORG001",
        "job_id": "JOB001",
        "correlation_id": "CORR001",
    },

    ApprovalDocument: {
        "org_id": "ORG001",
        "job_id": "JOB001",
        "exception_id": "EXCEPTION001",
        "decision": ApprovalDecision.APPROVE,
        "reviewer_id": "USER001",
        "reviewer_role": "FINANCE_MANAGER",
        "decided_at": NOW,
        "idempotency_key": "IDEMPOTENCY001",
        "request_fingerprint": "a" * 64,
    },

    AuditEventDocument: {
        "org_id": "ORG001",
        "seq": 1,
        "ts": NOW,
        "event_type": "EXCEPTION_REVIEWED",
        "actor": {
            "actor_type": "USER",
            "actor_id": "USER001",
        },
        "resource": {
            "resource_type": "EXCEPTION",
            "resource_id": "EXCEPTION001",
        },
        "action": "REVIEW",
        "outcome": AuditOutcome.SUCCESS,
        "correlation_id": "CORR001",
        "hash": "HASH001",
    },

    ReportDocument: {
        "org_id": "ORG001",
        "job_id": "JOB001",
        "format": "PDF",
        "storage_key": "reports/report001.pdf",
        "sha256": SHA256,
        "generated_by": "report_agent",
    },

    LLMUsageDocument: {
        "org_id": "ORG001",
        "job_id": "JOB001",
        "agent_name": "investigation_agent",
        "task": "investigation",
        "provider": "local",
        "model": "llama3.2:3b",
        "tier": "standard",
        "est_cost": Decimal("0.025"),
        "price_version": "v1",
        "latency_ms": 120,
        "correlation_id": "CORR001",
    },
}


TENANT_MODELS = [
    UserDocument,
    UploadedFileDocument,
    IngestionJobDocument,
    TransactionDocument,
    ReconciliationJobDocument,
    MatchResultDocument,
    ExceptionDocument,
    InvestigationDocument,
    AgentExecutionDocument,
    WorkflowRunDocument,
    ApprovalDocument,
    AuditEventDocument,
    ReportDocument,
    LLMUsageDocument,
]


# --------------------------------------------------
# Collection model tests
# --------------------------------------------------

def test_all_15_collection_models_import():
    assert len(SAMPLE_DOCUMENTS) == 15


@pytest.mark.parametrize(
    "model_class,payload",
    list(SAMPLE_DOCUMENTS.items()),
)
def test_collection_model_accepts_valid_document(
    model_class,
    payload,
):
    document = model_class.model_validate(payload)

    assert isinstance(document, model_class)


def test_all_tenant_models_inherit_tenant_document():
    assert len(TENANT_MODELS) == 14

    for model in TENANT_MODELS:
        assert issubclass(model, TenantDocument)


def test_organization_is_not_a_tenant_document():
    assert not issubclass(
        OrganizationDocument,
        TenantDocument,
    )


@pytest.mark.parametrize("model_class", TENANT_MODELS)
def test_every_tenant_model_requires_org_id(model_class):
    payload = dict(SAMPLE_DOCUMENTS[model_class])
    payload.pop("org_id")

    with pytest.raises(ValidationError):
        model_class.model_validate(payload)


# --------------------------------------------------
# Shared document foundation tests
# --------------------------------------------------

def test_document_base_generates_object_id():
    document = DocumentBase()

    assert document.id is not None


def test_document_base_generates_timestamps():
    document = DocumentBase()

    assert document.created_at.tzinfo is not None
    assert document.updated_at.tzinfo is not None


def test_document_base_has_schema_version():
    document = DocumentBase()

    assert document.schema_version == 1


# --------------------------------------------------
# Financial precision tests
# --------------------------------------------------

def test_money_serializes_to_decimal128():
    document = TransactionDocument.model_validate(
        SAMPLE_DOCUMENTS[TransactionDocument]
    )

    bson_document = model_to_bson_document(document)

    assert isinstance(
        bson_document["amount"],
        Decimal128,
    )

    assert (
        bson_document["amount"].to_decimal()
        == Decimal("7500.50")
    )


def test_money_rejects_float():
    adapter = TypeAdapter(Money)

    with pytest.raises(ValidationError):
        adapter.validate_python(7500.50)


def test_money_accepts_decimal_string():
    adapter = TypeAdapter(Money)

    result = adapter.validate_python("7500.50")

    assert result == Decimal("7500.50")
    assert isinstance(result, Decimal)


def test_decimal128_round_trip():
    original = Decimal("7500.50")

    stored = to_bson_value(original)
    restored = from_bson_value(stored)

    assert isinstance(stored, Decimal128)
    assert restored == original


# --------------------------------------------------
# Date validation tests
# --------------------------------------------------

def test_uploaded_file_accepts_valid_period():
    period = FilePeriod(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )

    assert period.start_date < period.end_date


def test_uploaded_file_rejects_invalid_period():
    with pytest.raises(ValidationError):
        FilePeriod(
            start_date=date(2026, 2, 1),
            end_date=date(2026, 1, 1),
        )


def test_reconciliation_accepts_valid_period():
    from app.models.reconciliation_job import ReconciliationPeriod

    period = ReconciliationPeriod(
        start_date=datetime(2026, 1, 1),
        end_date=datetime(2026, 1, 31),
    )

    assert period.start_date < period.end_date


def test_reconciliation_rejects_invalid_period():
    from app.models.reconciliation_job import ReconciliationPeriod

    with pytest.raises(ValidationError):
        ReconciliationPeriod(
            start_date=datetime(2026, 2, 1),
            end_date=datetime(2026, 1, 1),
        )


# --------------------------------------------------
# Enum validation tests
# --------------------------------------------------

def test_transaction_source_type_enum():
    assert SourceType.BANK.value == "BANK"
    assert SourceType.LEDGER.value == "LEDGER"
    assert SourceType.GATEWAY.value == "GATEWAY"


def test_transaction_direction_enum():
    assert TransactionDirection.CREDIT.value == "CREDIT"
    assert TransactionDirection.DEBIT.value == "DEBIT"


def test_transaction_validity_enum():
    assert TransactionValidity.VALID.value == "VALID"
    assert TransactionValidity.INVALID.value == "INVALID"


def test_approval_decision_enum():
    assert ApprovalDecision.APPROVE.value == "approve"
    assert ApprovalDecision.REJECT.value == "reject"
    assert ApprovalDecision.MODIFY.value == "modify"


# --------------------------------------------------
# Special model validation tests
# --------------------------------------------------

def test_report_signoff_uses_datetime():
    document = ReportDocument.model_validate(
        SAMPLE_DOCUMENTS[ReportDocument]
    )

    assert document.signoff.status == "PENDING"
    assert document.signoff.signed_at is None


def test_llm_usage_generates_utc_timestamp():
    document = LLMUsageDocument.model_validate(
        SAMPLE_DOCUMENTS[LLMUsageDocument]
    )

    assert isinstance(document.ts, datetime)
    assert document.ts.tzinfo is not None
    assert document.ts.utcoffset().total_seconds() == 0


def test_exception_requires_summary():
    payload = dict(SAMPLE_DOCUMENTS[ExceptionDocument])
    payload.pop("summary")

    with pytest.raises(ValidationError):
        ExceptionDocument.model_validate(payload)


def test_transaction_rejects_float_amount():
    payload = dict(SAMPLE_DOCUMENTS[TransactionDocument])
    payload["amount"] = 7500.50

    with pytest.raises(ValidationError):
        TransactionDocument.model_validate(payload)

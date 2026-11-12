
from decimal import Decimal

import pytest
from bson.decimal128 import Decimal128
from pydantic import TypeAdapter, ValidationError

from app.models.base import TenantDocument
from app.models.bson import Money, model_to_bson_document
from app.models.organization import OrganizationDocument
from app.models.user import UserDocument
from app.models.uploaded_file import UploadedFileDocument
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


ALL_MODELS = [
    OrganizationDocument,
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


def test_all_15_collection_models_import():
    assert len(ALL_MODELS) == 15


def test_all_tenant_models_inherit_tenant_document():
    assert len(TENANT_MODELS) == 14

    for model in TENANT_MODELS:
        assert issubclass(model, TenantDocument)


def test_organization_is_not_a_tenant_document():
    assert not issubclass(OrganizationDocument, TenantDocument)


def test_tenant_models_require_org_id():
    with pytest.raises(ValidationError):
        UserDocument(email="user@example.com")


def test_money_serializes_to_decimal128():
    class MoneyTestDocument(TenantDocument):
        amount: Money

    document = MoneyTestDocument(
        org_id="ORG001",
        amount=Decimal("1250.50"),
    )

    bson_document = model_to_bson_document(document)

    assert isinstance(bson_document["amount"], Decimal128)
    assert bson_document["amount"].to_decimal() == Decimal("1250.50")


def test_money_rejects_float():
    adapter = TypeAdapter(Money)

    with pytest.raises(ValidationError):
        adapter.validate_python(1250.50)

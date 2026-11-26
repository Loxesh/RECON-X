
"""Immutable human approval decision document."""

from datetime import datetime
from typing import Any

from pydantic import Field

from app.models.base import TenantDocument
from app.models.enums import ApprovalDecision


class ApprovalDocument(TenantDocument):
    job_id: str = Field(min_length=1)
    exception_id: str = Field(min_length=1)

    decision: ApprovalDecision
    reviewer_id: str = Field(min_length=1)
    reviewer_role: str = Field(min_length=1)

    comment: str | None = Field(default=None, max_length=4000)
    before: dict[str, Any] = Field(default_factory=dict)
    after: dict[str, Any] = Field(default_factory=dict)

    idempotency_key: str = Field(min_length=1, max_length=128)
    request_fingerprint: str = Field(min_length=64, max_length=64)

    decided_at: datetime
    policy_snapshot: dict[str, Any] = Field(default_factory=dict)

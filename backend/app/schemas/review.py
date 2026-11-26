
"""Request and response schemas for human reviews."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ApprovalDecision


class ReviewDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: ApprovalDecision
    comment: str | None = Field(default=None, max_length=4000)
    after: dict[str, Any] = Field(default_factory=dict)


class ReviewQueueItem(BaseModel):
    id: str
    job_id: str
    type: str
    severity: str
    summary: str
    status: str
    review_required: bool
    created_at: datetime


class ReviewDetailResponse(BaseModel):
    id: str
    job_id: str
    type: str
    severity: str
    summary: str
    primary_txn_ids: list[str]
    related_match_ids: list[str]
    status: str
    review_required: bool
    risk: dict[str, Any]
    evidence: dict[str, Any]
    investigation_id: str | None
    assigned_to: str | None
    created_at: datetime


class ReviewDecisionResponse(BaseModel):
    id: str
    exception_id: str
    job_id: str
    decision: ApprovalDecision
    reviewer_id: str
    reviewer_role: str
    comment: str | None
    before: dict[str, Any]
    after: dict[str, Any]
    decided_at: datetime
    replayed: bool = False

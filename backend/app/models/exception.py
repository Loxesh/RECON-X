
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.base import TenantDocument

class ExceptionStatusChange(BaseModel):
    """Records a status transition in an exception's history."""

    model_config = ConfigDict(extra="forbid")

    status: str = Field(min_length=1)
    changed_by: str = Field(min_length=1)
    changed_at: datetime
    comment: str | None = None

class ExceptionDocument(TenantDocument):
    """MongoDB document representing a reconciliation exception."""

    job_id: str = Field(min_length=1)

    type: str = Field(min_length=1)
    severity: str = Field(min_length=1)
    summary: str = Field(min_length=1, max_length=2000)

    primary_txn_ids: list[str] = Field(default_factory=list)
    related_match_ids: list[str] = Field(default_factory=list)

    status: str = "OPEN"
    review_required: bool = True

    risk: dict[str, Any] = Field(default_factory=dict)
    evidence: dict[str, Any] = Field(default_factory=dict)

    investigation_id: str | None = None
    status_history: list[ExceptionStatusChange] = Field(
        default_factory=list
    )
    assigned_to: str | None = None
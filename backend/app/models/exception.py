
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.base import TenantDocument


class ExceptionStatusChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    changed_by: str
    changed_at: datetime
    comment: str | None = None


class ExceptionDocument(TenantDocument):
    job_id: str = Field(min_length=1)

    type: str = Field(min_length=1)
    severity: str = Field(min_length=1)

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


from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.common import ApiSchema


class ExceptionStatusHistoryItem(ApiSchema):
    """A recorded exception status transition."""

    status: str = Field(min_length=1)
    changed_by: str = Field(min_length=1)
    changed_at: datetime
    comment: str | None = None


class ExceptionResponse(ApiSchema):
    """Exception details returned to the frontend."""

    id: str
    job_id: str

    type: str
    severity: str
    summary: str

    primary_txn_ids: list[str] = Field(default_factory=list)
    related_match_ids: list[str] = Field(default_factory=list)

    status: str
    review_required: bool

    risk: dict[str, Any] = Field(default_factory=dict)
    evidence: dict[str, Any] = Field(default_factory=dict)

    investigation_id: str | None = None
    status_history: list[ExceptionStatusHistoryItem] = Field(
        default_factory=list
    )
    assigned_to: str | None = None


class ExceptionListFilters(ApiSchema):
    """Filters for exception list endpoints."""

    job_id: str | None = None
    type: str | None = None
    severity: str | None = None
    status: str | None = None
    assigned_to: str | None = None


class ExceptionAssignmentRequest(ApiSchema):
    """Request to assign an exception to a reviewer."""

    assigned_to: str = Field(min_length=1)


class ExceptionStatusUpdateRequest(ApiSchema):
    """Request to update an exception's review status."""

    status: str = Field(min_length=1)
    comment: str | None = None


from datetime import date, datetime
from typing import Any

from pydantic import Field, model_validator

from app.schemas.common import ApiSchema


class JobPeriodSchema(ApiSchema):
    """Date range selected for a reconciliation job."""

    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_period(self):
        if self.start_date > self.end_date:
            raise ValueError(
                "Period start date cannot be after end date."
            )
        return self


class ReconciliationFileSelection(ApiSchema):
    """Uploaded files selected for reconciliation."""

    bank: str | None = None
    ledger: str | None = None
    gateway: str | None = None


class ReconciliationJobCreateRequest(ApiSchema):
    """API request to create a reconciliation job."""

    name: str = Field(min_length=2, max_length=150)
    period: JobPeriodSchema
    file_ids: ReconciliationFileSelection
    idempotency_key: str = Field(min_length=1, max_length=150)


class ReconciliationJobResponse(ApiSchema):
    """Safe reconciliation job details returned by the API."""

    id: str
    name: str
    status: str
    period: JobPeriodSchema
    file_ids: ReconciliationFileSelection
    stats: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    completed_at: datetime | None = None


class ReconciliationJobListItem(ApiSchema):
    """Compact reconciliation job information for list views."""

    id: str
    name: str
    status: str
    created_at: datetime
    completed_at: datetime | None = None

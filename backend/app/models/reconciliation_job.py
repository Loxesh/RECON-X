
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.models.base import TenantDocument

class ReconciliationPeriod(BaseModel):
    """Date range covered by a reconciliation job."""

    start_date: datetime
    end_date: datetime

    @model_validator(mode="after")
    def validate_period(self):
        if self.start_date > self.end_date:
            raise ValueError(
                "Period start date cannot be after end date."
            )
        return self

class ReconciliationFileIds(BaseModel):
    """Uploaded files selected for reconciliation."""

    bank: str | None = None
    ledger: str | None = None
    gateway: str | None = None

class ReconciliationJobDocument(TenantDocument):
    """MongoDB document representing a reconciliation job."""

    name: str = Field(min_length=2, max_length=150)
    period: ReconciliationPeriod
    status: str = "PENDING"
    idempotency_key: str = Field(min_length=1)

    file_ids: ReconciliationFileIds
    rules_snapshot: dict[str, Any] = Field(default_factory=dict)
    stats: dict[str, Any] = Field(default_factory=dict)

    workflow_run_id: str | None = None
    created_by: str = Field(min_length=1)
    completed_at: datetime | None = None
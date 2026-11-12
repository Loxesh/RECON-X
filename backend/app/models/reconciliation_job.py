
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.base import TenantDocument


class ReconciliationPeriod(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_date: datetime
    end_date: datetime


class ReconciliationFiles(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bank: str | None = None
    ledger: str | None = None
    gateway: str | None = None


class ReconciliationJobDocument(TenantDocument):
    name: str = Field(min_length=1, max_length=150)
    period: ReconciliationPeriod
    status: str = "PENDING"

    idempotency_key: str = Field(min_length=1)
    file_ids: ReconciliationFiles

    rules_snapshot: dict[str, Any] = Field(default_factory=dict)
    stats: dict[str, Any] = Field(default_factory=dict)

    workflow_run_id: str | None = None
    created_by: str = Field(min_length=1)
    completed_at: datetime | None = None

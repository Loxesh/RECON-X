
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.base import TenantDocument


class IngestionCounts(BaseModel):
    total: int = Field(default=0, ge=0)
    valid: int = Field(default=0, ge=0)
    invalid: int = Field(default=0, ge=0)


class IngestionError(BaseModel):
    row_number: int | None = None
    error_code: str
    message: str


class IngestionJobDocument(TenantDocument):
    file_id: str
    status: str = "PENDING"
    counts: IngestionCounts = Field(default_factory=IngestionCounts)
    mapping: dict[str, Any] = Field(default_factory=dict)
    errors_summary: list[IngestionError] = Field(default_factory=list)
    started_at: datetime | None = None
    finished_at: datetime | None = None

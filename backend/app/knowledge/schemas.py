"""Validated contracts for tenant-scoped historical research."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ResearchQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    org_id: str = Field(min_length=1, max_length=100)
    current_job_id: str = Field(min_length=1, max_length=128)
    exception_id: str | None = Field(default=None, max_length=128)
    limit: int = Field(default=20, ge=1, le=100)


class ResearchRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str
    record_type: str
    job_id: str | None = None
    summary: str
    occurred_at: datetime | None = None
    citation: str
    details: dict[str, Any] = Field(default_factory=dict)


class ResearchToolResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    records: list[ResearchRecord] = Field(default_factory=list)
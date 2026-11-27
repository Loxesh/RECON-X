"""Validated Research Agent input and output schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ResearchAgentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exception_id: str | None = Field(default=None, max_length=128)
    limit: int = Field(default=20, ge=1, le=100)


class HistoricalEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str
    record_type: str
    job_id: str | None = None
    summary: str
    occurred_at: datetime | None = None
    citation: str
    details: dict[str, Any] = Field(default_factory=dict)


class ResearchAgentOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    org_id: str
    current_job_id: str
    evidence: list[HistoricalEvidence] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)
    retrieved_count: int = Field(ge=0)
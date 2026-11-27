"""Strict input and output schemas for exception investigation."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class InvestigationEvidence(BaseModel):
    """One evidence record supplied by a trusted backend service."""

    model_config = ConfigDict(extra="forbid", strict=True)

    record_id: str = Field(min_length=1, max_length=128)
    record_type: str = Field(min_length=1, max_length=100)
    summary: str = Field(min_length=1, max_length=4000)
    details: dict[str, Any] = Field(default_factory=dict)


class InvestigationAgentInput(BaseModel):
    """Evidence and task context for an exception investigation."""

    model_config = ConfigDict(extra="forbid", strict=True)

    exception_id: str = Field(min_length=1, max_length=128)
    task_context: str = Field(min_length=1, max_length=4000)
    evidence: list[InvestigationEvidence] = Field(min_length=1, max_length=100)


class InvestigationClaim(BaseModel):
    """A claim linked to supplied evidence."""

    model_config = ConfigDict(extra="forbid", strict=True)

    claim: str = Field(min_length=1, max_length=2000)
    evidence_record_ids: list[str] = Field(min_length=1, max_length=20)


class InvestigationAgentOutput(BaseModel):
    """Explanation-only result; deliberately excludes decision fields."""

    model_config = ConfigDict(extra="forbid", strict=True)

    exception_id: str
    explanation: str = Field(min_length=1, max_length=8000)
    claims: list[InvestigationClaim] = Field(min_length=1, max_length=20)
    cited_record_ids: list[str] = Field(min_length=1, max_length=100)
    recommended_actions: list[str] = Field(default_factory=list, max_length=10)

    provider: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=200)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    latency_ms: int = Field(ge=0)
    fallback_used: bool
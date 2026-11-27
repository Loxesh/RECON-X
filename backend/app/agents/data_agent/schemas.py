"""Schemas for canonical transaction quality inspection."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.transaction import TransactionDocument


class DataAgentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    records: list[TransactionDocument] = Field(min_length=1, max_length=5000)
    source_metadata: dict[str, Any] = Field(default_factory=dict)


class QualityFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transaction_id: str
    code: str
    severity: str
    message: str
    evidence_id: str


class DataAgentOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    inspected_count: int = Field(ge=0)
    finding_count: int = Field(ge=0)
    findings: list[QualityFinding] = Field(default_factory=list)
    flags_by_transaction: dict[str, list[str]] = Field(default_factory=dict)
    evidence_ids: list[str] = Field(default_factory=list)
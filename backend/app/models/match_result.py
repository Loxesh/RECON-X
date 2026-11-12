
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.base import TenantDocument
from app.models.bson import Money
from app.models.enums import (
    ConfidenceLabel,
    MatchOrigin,
    MatchType,
)


class MatchRelationship(BaseModel):
    model_config = ConfigDict(extra="forbid")

    side_a: str
    side_b: str


class MatchResultDocument(TenantDocument):
    job_id: str = Field(min_length=1)

    relationship: MatchRelationship
    match_type: MatchType
    status: str = "PROPOSED"
    origin: MatchOrigin

    rule_id: str | None = None
    side_a_ids: list[str] = Field(min_length=1)
    side_b_ids: list[str] = Field(min_length=1)

    amount_a: Money
    amount_b: Money
    difference: Money

    score: int = Field(ge=0, le=100)
    confidence: ConfidenceLabel

    evidence: dict[str, Any] = Field(default_factory=dict)
    confirmed_by: str | None = None

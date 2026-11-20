from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import SourceType


class MatchOutcome(str, Enum):
    CONFIRMED_AUTO = "CONFIRMED_AUTO"
    SUGGESTED = "SUGGESTED"
    AMBIGUOUS = "AMBIGUOUS"
    UNMATCHED = "UNMATCHED"


class MatchRule(str, Enum):
    EXACT = "EXACT_01"
    REFERENCE = "REF_01"
    TOLERANCE = "TOL_01"
    FUZZY = "FUZZY_01"
    AGGREGATE = "AGG_01"


class MatchingTransaction(BaseModel):
    """Canonical transaction fields used by matching rules."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    transaction_id: str = Field(min_length=1)
    source_type: SourceType
    transaction_reference: str | None = None
    reference_norm: str | None = None
    transaction_date: datetime
    amount: Decimal
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    fingerprint: str = Field(min_length=1)
    description_norm: str | None = None

    @field_validator("amount", mode="before")
    @classmethod
    def validate_decimal_amount(cls, value: Any) -> Decimal:
        if isinstance(value, (float, bool)):
            raise ValueError("Amount must not be a float or boolean.")

        try:
            amount = Decimal(str(value))
        except Exception as exc:
            raise ValueError("Amount must be a valid Decimal value.") from exc

        if not amount.is_finite():
            raise ValueError("Amount must be finite.")

        if amount < 0:
            raise ValueError("Amount cannot be negative.")

        return amount


class MatchingPairInput(BaseModel):
    """Two canonical transactions presented for comparison."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    left: MatchingTransaction
    right: MatchingTransaction
    ruleset_version: str = Field(min_length=1)
    ruleset_hash: str = Field(min_length=64, max_length=64)


class MatchEvidence(BaseModel):
    """Auditable explanation for a matching outcome."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    rule_id: str = Field(min_length=1)
    rule_priority: int = Field(ge=0)
    reason: str = Field(min_length=1)
    compared_fields: tuple[str, ...] = ()
    observed_values: dict[str, str] = Field(default_factory=dict)


class MatchingResult(BaseModel):
    """Structured result returned by a matching pass."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    outcome: MatchOutcome
    rule_id: str | None = None
    transaction_ids: tuple[str, ...] = ()
    evidence: tuple[MatchEvidence, ...] = ()
    candidate_score: Decimal | None = None
    ruleset_version: str = Field(min_length=1)
    ruleset_hash: str = Field(min_length=64, max_length=64)

    @field_validator("candidate_score", mode="before")
    @classmethod
    def validate_candidate_score(cls, value: Any) -> Decimal | None:
        if value is None:
            return None

        if isinstance(value, (float, bool)):
            raise ValueError("Candidate score must not be a float or boolean.")

        try:
            score = Decimal(str(value))
        except Exception as exc:
            raise ValueError("Candidate score must be a valid Decimal.") from exc

        if not score.is_finite() or not Decimal("0") <= score <= Decimal("1"):
            raise ValueError("Candidate score must be between 0 and 1.")

        return score
"""Validated schemas for the Matching Agent."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.reconciliation.rules import MatchingRuleset
from app.reconciliation.schemas import MatchingTransaction


class AggregateCandidateInput(BaseModel):
    """Explicitly supplied aggregate candidate transaction IDs."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    left_transaction_ids: tuple[str, ...] = Field(min_length=1)
    right_transaction_ids: tuple[str, ...] = Field(min_length=1)


class MatchingAgentInput(BaseModel):
    """Canonical transactions and approved matching configuration."""

    model_config = ConfigDict(extra="forbid")

    bank_transactions: list[MatchingTransaction] = Field(default_factory=list)
    ledger_transactions: list[MatchingTransaction] = Field(default_factory=list)
    gateway_transactions: list[MatchingTransaction] = Field(default_factory=list)

    ruleset: MatchingRuleset = Field(default_factory=MatchingRuleset)

    bank_aggregate_candidates: list[AggregateCandidateInput] = Field(
        default_factory=list
    )
    gateway_aggregate_candidates: list[AggregateCandidateInput] = Field(
        default_factory=list
    )


class MatchingAgentOutput(BaseModel):
    """Serialized deterministic engine result.

    The engine remains the sole authority for match outcomes.
    """

    model_config = ConfigDict(extra="forbid")

    bank_ledger: dict[str, Any]
    gateway_ledger: dict[str, Any]
    consolidated_status: dict[str, Any]
    ruleset_version: str
    ruleset_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
"""Matching Agent delegates all matching to the deterministic engine."""

from dataclasses import fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from app.agents.base_agent import AgentContext, BaseAgent
from app.agents.matching_agent.schemas import (
    MatchingAgentInput,
    MatchingAgentOutput,
)
from app.agents.tool_registry import ToolRegistry
from app.reconciliation.engine import (
    AggregateCandidateGroup,
    run_reconciliation,
)


def _serialize_engine_value(value: Any) -> Any:
    """Convert engine dataclasses into JSON-compatible validated data."""

    if isinstance(value, Enum):
        return value.value

    if isinstance(value, Decimal):
        return str(value)

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if is_dataclass(value) and not isinstance(value, type):
        return {
            item.name: _serialize_engine_value(getattr(value, item.name))
            for item in fields(value)
        }

    if isinstance(value, dict):
        return {
            str(key): _serialize_engine_value(item)
            for key, item in value.items()
        }

    if isinstance(value, (tuple, list, set, frozenset)):
        return [_serialize_engine_value(item) for item in value]

    return value


class MatchingAgent(BaseAgent[MatchingAgentInput, MatchingAgentOutput]):
    """Thin agent adapter around the deterministic reconciliation engine."""

    agent_name = "matching_agent"
    input_model = MatchingAgentInput
    output_model = MatchingAgentOutput

    async def execute(
        self,
        input_data: MatchingAgentInput,
        context: AgentContext,
    ) -> MatchingAgentOutput:
        # The agent performs no matching, scoring, classification or decisions.
        # All such work remains inside the approved deterministic engine.
        result = run_reconciliation(
            bank_transactions=input_data.bank_transactions,
            ledger_transactions=input_data.ledger_transactions,
            gateway_transactions=input_data.gateway_transactions,
            ruleset=input_data.ruleset,
            bank_aggregate_candidates=tuple(
                AggregateCandidateGroup(
                    left_transaction_ids=item.left_transaction_ids,
                    right_transaction_ids=item.right_transaction_ids,
                )
                for item in input_data.bank_aggregate_candidates
            ),
            gateway_aggregate_candidates=tuple(
                AggregateCandidateGroup(
                    left_transaction_ids=item.left_transaction_ids,
                    right_transaction_ids=item.right_transaction_ids,
                )
                for item in input_data.gateway_aggregate_candidates
            ),
        )

        return MatchingAgentOutput(
            bank_ledger=_serialize_engine_value(result.bank_ledger),
            gateway_ledger=_serialize_engine_value(result.gateway_ledger),
            consolidated_status=_serialize_engine_value(
                result.consolidated_status
            ),
            ruleset_version=result.ruleset_version,
            ruleset_hash=result.ruleset_hash,
        )

    @classmethod
    def create(
        cls,
        tool_registry: ToolRegistry,
        timeout_seconds: float = 60.0,
    ) -> "MatchingAgent":
        return cls(
            tool_registry=tool_registry,
            timeout_seconds=timeout_seconds,
        )
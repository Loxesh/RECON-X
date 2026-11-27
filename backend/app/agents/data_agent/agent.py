"""Deterministic Data Agent operating on canonical transactions."""

from collections import defaultdict

from app.agents.base_agent import AgentContext, BaseAgent
from app.agents.data_agent.schemas import (
    DataAgentInput,
    DataAgentOutput,
    QualityFinding,
)
from app.agents.tool_registry import ToolRegistry
from app.models.enums import TransactionValidity


class DataAgent(BaseAgent[DataAgentInput, DataAgentOutput]):
    agent_name = "data_agent"
    input_model = DataAgentInput
    output_model = DataAgentOutput

    async def execute(
        self,
        input_data: DataAgentInput,
        context: AgentContext,
    ) -> DataAgentOutput:
        findings: list[QualityFinding] = []
        flags: dict[str, list[str]] = defaultdict(list)
        evidence_ids: list[str] = []

        def add_finding(
            transaction_id: str,
            code: str,
            severity: str,
            message: str,
        ) -> None:
            evidence_id = transaction_id

            findings.append(
                QualityFinding(
                    transaction_id=transaction_id,
                    code=code,
                    severity=severity,
                    message=message,
                    evidence_id=evidence_id,
                )
            )

            if code not in flags[transaction_id]:
                flags[transaction_id].append(code)

            if evidence_id not in evidence_ids:
                evidence_ids.append(evidence_id)

        for record in input_data.records:
            transaction_id = str(record.id)

            if record.validity == TransactionValidity.INVALID:
                add_finding(
                    transaction_id,
                    "INVALID_TRANSACTION",
                    "HIGH",
                    "The canonical transaction is marked invalid.",
                )

            if record.validation_errors:
                add_finding(
                    transaction_id,
                    "VALIDATION_ERRORS_PRESENT",
                    "HIGH",
                    "The canonical transaction contains validation errors.",
                )

            if not (record.reference_norm or "").strip():
                add_finding(
                    transaction_id,
                    "MISSING_REFERENCE",
                    "MEDIUM",
                    "The transaction has no normalised reference.",
                )

            if not (record.description_norm or "").strip():
                add_finding(
                    transaction_id,
                    "MISSING_NORMALISED_DESCRIPTION",
                    "LOW",
                    "The transaction has no normalised description.",
                )

        return DataAgentOutput(
            inspected_count=len(input_data.records),
            finding_count=len(findings),
            findings=findings,
            flags_by_transaction=dict(flags),
            evidence_ids=evidence_ids,
        )

    @classmethod
    def create(
        cls,
        tool_registry: ToolRegistry,
        timeout_seconds: float = 30.0,
    ) -> "DataAgent":
        return cls(
            tool_registry=tool_registry,
            timeout_seconds=timeout_seconds,
        )
from enum import Enum
from typing import Mapping

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import RiskLevel
from app.reconciliation.discrepancy_detector import (
    DiscrepancyEvidence,
    DiscrepancyType,
)


class ExceptionLifecycle(str, Enum):
    OPEN = "OPEN"


class SuggestedAction(str, Enum):
    REVIEW_AMOUNT = "REVIEW_AMOUNT"
    VERIFY_TRANSACTION_DATE = "VERIFY_TRANSACTION_DATE"
    VERIFY_REFERENCE = "VERIFY_REFERENCE"
    VERIFY_CURRENCY = "VERIFY_CURRENCY"
    VERIFY_SOURCE_STATUS = "VERIFY_SOURCE_STATUS"


DEFAULT_SEVERITY_POLICY: dict[DiscrepancyType, RiskLevel] = {
    DiscrepancyType.AMOUNT_MISMATCH: RiskLevel.MEDIUM,
    DiscrepancyType.DATE_MISMATCH: RiskLevel.MEDIUM,
    DiscrepancyType.REFERENCE_MISMATCH: RiskLevel.MEDIUM,
    DiscrepancyType.CURRENCY_MISMATCH: RiskLevel.HIGH,
    DiscrepancyType.STATUS_MISMATCH: RiskLevel.HIGH,
}

SUGGESTED_ACTIONS: dict[DiscrepancyType, SuggestedAction] = {
    DiscrepancyType.AMOUNT_MISMATCH: SuggestedAction.REVIEW_AMOUNT,
    DiscrepancyType.DATE_MISMATCH: SuggestedAction.VERIFY_TRANSACTION_DATE,
    DiscrepancyType.REFERENCE_MISMATCH: SuggestedAction.VERIFY_REFERENCE,
    DiscrepancyType.CURRENCY_MISMATCH: SuggestedAction.VERIFY_CURRENCY,
    DiscrepancyType.STATUS_MISMATCH: SuggestedAction.VERIFY_SOURCE_STATUS,
}

# When several discrepancy types exist for the same transaction pair,
# select one primary type and preserve all findings as supporting evidence.
PRIMARY_TYPE_PRIORITY = (
    DiscrepancyType.CURRENCY_MISMATCH,
    DiscrepancyType.STATUS_MISMATCH,
    DiscrepancyType.AMOUNT_MISMATCH,
    DiscrepancyType.REFERENCE_MISMATCH,
    DiscrepancyType.DATE_MISMATCH,
)


class ClassifiedException(BaseModel):
    """Deterministic exception classification ready for later persistence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    exception_type: DiscrepancyType
    severity: RiskLevel
    primary_txn_ids: tuple[str, ...] = Field(min_length=2)
    reason: str = Field(min_length=1)
    lifecycle_state: ExceptionLifecycle = ExceptionLifecycle.OPEN
    review_required: bool = True
    suggested_action: SuggestedAction
    evidence: tuple[DiscrepancyEvidence, ...] = Field(min_length=1)


def classify_discrepancies(
    findings: tuple[DiscrepancyEvidence, ...] | list[DiscrepancyEvidence],
    severity_policy: Mapping[DiscrepancyType, RiskLevel] | None = None,
) -> tuple[ClassifiedException, ...]:
    """
    Group findings by transaction pair and assign one primary exception type.

    Severity defaults are conservative starting classifications. A caller
    may provide an organisation-approved policy override. This function
    never approves, rejects, or changes a financial transaction.
    """
    if not findings:
        return ()

    policy = dict(DEFAULT_SEVERITY_POLICY)
    if severity_policy is not None:
        for discrepancy_type, severity in severity_policy.items():
            if not isinstance(discrepancy_type, DiscrepancyType):
                raise ValueError("Severity policy keys must be DiscrepancyType values.")
            if not isinstance(severity, RiskLevel):
                raise ValueError("Severity policy values must be RiskLevel values.")
            policy[discrepancy_type] = severity

    grouped: dict[tuple[str, ...], list[DiscrepancyEvidence]] = {}
    for finding in findings:
        key = tuple(sorted(finding.transaction_ids))
        grouped.setdefault(key, []).append(finding)

    results: list[ClassifiedException] = []
    for transaction_ids, group in sorted(grouped.items()):
        present_types = {item.discrepancy_type for item in group}
        primary_type = next(
            item for item in PRIMARY_TYPE_PRIORITY if item in present_types
        )
        primary = next(
            item for item in group if item.discrepancy_type == primary_type
        )
        ordered_evidence = tuple(
            sorted(group, key=lambda item: item.discrepancy_type.value)
        )

        results.append(
            ClassifiedException(
                exception_type=primary_type,
                severity=policy[primary_type],
                primary_txn_ids=transaction_ids,
                reason=primary.reason,
                lifecycle_state=ExceptionLifecycle.OPEN,
                review_required=True,
                suggested_action=SUGGESTED_ACTIONS[primary_type],
                evidence=ordered_evidence,
            )
        )

    return tuple(results)
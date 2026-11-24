from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import SourceType
from app.reconciliation.rules import MatchingRuleset
from app.reconciliation.schemas import MatchingTransaction


class DiscrepancyType(str, Enum):
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    DATE_MISMATCH = "DATE_MISMATCH"
    REFERENCE_MISMATCH = "REFERENCE_MISMATCH"
    CURRENCY_MISMATCH = "CURRENCY_MISMATCH"
    STATUS_MISMATCH = "STATUS_MISMATCH"


class DiscrepancyInput(BaseModel):
    """A transaction pair and optional source-system statuses to compare."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    left: MatchingTransaction
    right: MatchingTransaction
    left_status: str | None = Field(default=None, min_length=1)
    right_status: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_pair(self):
        supported_pairs = {
            (SourceType.BANK, SourceType.LEDGER),
            (SourceType.LEDGER, SourceType.BANK),
            (SourceType.GATEWAY, SourceType.LEDGER),
            (SourceType.LEDGER, SourceType.GATEWAY),
        }
        if (self.left.source_type, self.right.source_type) not in supported_pairs:
            raise ValueError(
                "Unsupported source combination for discrepancy detection."
            )

        if (self.left_status is None) != (self.right_status is None):
            raise ValueError(
                "Both statuses must be provided together, or both omitted."
            )
        return self


class DiscrepancyEvidence(BaseModel):
    """Immutable, auditable evidence for one detected discrepancy."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    discrepancy_type: DiscrepancyType
    transaction_ids: tuple[str, str]
    source_types: tuple[str, str]
    reason: str = Field(min_length=1)
    compared_fields: tuple[str, ...]
    observed_values: dict[str, str] = Field(default_factory=dict)
    difference: Decimal | None = None
    threshold: Decimal | int | None = None

    @field_validator("difference", mode="before")
    @classmethod
    def validate_difference(cls, value: Any) -> Decimal | None:
        if value is None:
            return None
        if isinstance(value, (float, bool)):
            raise ValueError("Discrepancy differences must not use floats.")
        result = Decimal(str(value))
        if not result.is_finite() or result < 0:
            raise ValueError("Difference must be finite and non-negative.")
        return result

    @field_validator("threshold", mode="before")
    @classmethod
    def validate_threshold(cls, value: Any) -> Decimal | int | None:
        if value is None:
            return None
        if isinstance(value, bool):
            raise ValueError("Threshold must not be a boolean.")
        if isinstance(value, float):
            raise ValueError("Threshold must not use a float.")
        if isinstance(value, int):
            if value < 0:
                raise ValueError("Threshold must be non-negative.")
            return value
        result = Decimal(str(value))
        if not result.is_finite() or result < 0:
            raise ValueError("Threshold must be finite and non-negative.")
        return result


def _date_window_days(
    left_source: SourceType,
    right_source: SourceType,
    ruleset: MatchingRuleset,
) -> int:
    pair = {left_source, right_source}
    if pair == {SourceType.BANK, SourceType.LEDGER}:
        return ruleset.bank_ledger_date_window_days
    if pair == {SourceType.GATEWAY, SourceType.LEDGER}:
        return ruleset.gateway_ledger_date_window_days
    raise ValueError("Unsupported source combination for date comparison.")


def _normalise_reference(transaction: MatchingTransaction) -> str | None:
    value = transaction.reference_norm or transaction.transaction_reference
    if value is None:
        return None
    normalised = " ".join(value.strip().upper().split())
    return normalised or None


def detect_discrepancies(
    discrepancy_input: DiscrepancyInput,
    ruleset: MatchingRuleset,
) -> tuple[DiscrepancyEvidence, ...]:
    """
    Compare a supported source pair deterministically.

    Amount comparisons are performed only when currencies agree. The
    ruleset's suggested amount tolerance and source-specific date window
    determine whether a difference is classified as a discrepancy.
    """
    left = discrepancy_input.left
    right = discrepancy_input.right

    if left.transaction_id == right.transaction_id:
        raise ValueError("Compared transactions must have different internal IDs.")

    findings: list[DiscrepancyEvidence] = []
    ids = (left.transaction_id, right.transaction_id)
    sources = (left.source_type.value, right.source_type.value)

    if left.currency != right.currency:
        findings.append(
            DiscrepancyEvidence(
                discrepancy_type=DiscrepancyType.CURRENCY_MISMATCH,
                transaction_ids=ids,
                source_types=sources,
                reason="Transactions use different currencies; no implicit FX conversion is permitted.",
                compared_fields=("currency",),
                observed_values={
                    "left_currency": left.currency,
                    "right_currency": right.currency,
                },
            )
        )
    else:
        amount_difference = abs(left.amount - right.amount)
        threshold = ruleset.suggested_amount_tolerance
        if amount_difference > threshold:
            findings.append(
                DiscrepancyEvidence(
                    discrepancy_type=DiscrepancyType.AMOUNT_MISMATCH,
                    transaction_ids=ids,
                    source_types=sources,
                    reason="Transaction amount difference exceeds the configured suggested tolerance.",
                    compared_fields=("amount", "currency"),
                    observed_values={
                        "left_amount": str(left.amount),
                        "right_amount": str(right.amount),
                        "currency": left.currency,
                    },
                    difference=amount_difference,
                    threshold=threshold,
                )
            )

    date_difference = abs(
        (left.transaction_date.date() - right.transaction_date.date()).days
    )
    date_threshold = _date_window_days(left.source_type, right.source_type, ruleset)
    if date_difference > date_threshold:
        findings.append(
            DiscrepancyEvidence(
                discrepancy_type=DiscrepancyType.DATE_MISMATCH,
                transaction_ids=ids,
                source_types=sources,
                reason="Transaction date difference exceeds the configured source-pair date window.",
                compared_fields=("transaction_date",),
                observed_values={
                    "left_date": left.transaction_date.date().isoformat(),
                    "right_date": right.transaction_date.date().isoformat(),
                },
                difference=Decimal(date_difference),
                threshold=date_threshold,
            )
        )

    left_reference = _normalise_reference(left)
    right_reference = _normalise_reference(right)
    if (
        left_reference is not None
        and right_reference is not None
        and left_reference != right_reference
    ):
        findings.append(
            DiscrepancyEvidence(
                discrepancy_type=DiscrepancyType.REFERENCE_MISMATCH,
                transaction_ids=ids,
                source_types=sources,
                reason="Both transactions contain references, but their normalised values differ.",
                compared_fields=("reference_norm",),
                observed_values={
                    "left_reference": left_reference,
                    "right_reference": right_reference,
                },
            )
        )

    if discrepancy_input.left_status is not None:
        left_status = discrepancy_input.left_status.strip().upper()
        right_status = discrepancy_input.right_status.strip().upper()
        if left_status != right_status:
            findings.append(
                DiscrepancyEvidence(
                    discrepancy_type=DiscrepancyType.STATUS_MISMATCH,
                    transaction_ids=ids,
                    source_types=sources,
                    reason="Source systems report different transaction statuses.",
                    compared_fields=("status",),
                    observed_values={
                        "left_status": left_status,
                        "right_status": right_status,
                    },
                )
            )

    return tuple(
        sorted(findings, key=lambda item: item.discrepancy_type.value)
    )
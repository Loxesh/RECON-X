
"""Deterministic source-presence comparison for unmatched transactions."""

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from app.models.enums import SourceType
from app.reconciliation.schemas import MatchingTransaction


class MissingClassification(str, Enum):
    MISSING_FROM_BANK = "MISSING_FROM_BANK"
    MISSING_FROM_LEDGER = "MISSING_FROM_LEDGER"
    MISSING_FROM_GATEWAY = "MISSING_FROM_GATEWAY"


@dataclass(frozen=True)
class MissingEvidence:
    classification: MissingClassification
    transaction_id: str
    transaction_source: str
    missing_source: str
    reason: str
    compared_fields: tuple[str, ...]
    observed_values: tuple[tuple[str, str], ...]


_SUPPORTED_SOURCE_PAIRS = {
    frozenset({SourceType.BANK, SourceType.LEDGER}),
    frozenset({SourceType.GATEWAY, SourceType.LEDGER}),
}


def detect_missing_transactions(
    left_transactions: Iterable[MatchingTransaction],
    right_transactions: Iterable[MatchingTransaction],
    *,
    expected_left_source: SourceType,
    expected_right_source: SourceType,
) -> tuple[MissingEvidence, ...]:
    """Classify unmatched records absent from the opposite source.

    Supply the expected source types explicitly. Either collection may be
    empty, but the source pair must be an approved BANK–LEDGER or
    GATEWAY–LEDGER relationship.

    Inputs must already have passed through the matching cascade.
    """

    if frozenset(
        {expected_left_source, expected_right_source}
    ) not in _SUPPORTED_SOURCE_PAIRS:
        raise ValueError("Unsupported source combination for missing detection.")

    if expected_left_source == expected_right_source:
        raise ValueError("Expected source types must be different.")

    left = tuple(left_transactions)
    right = tuple(right_transactions)

    if any(
        item.source_type != expected_left_source for item in left
    ):
        raise ValueError("Left transactions do not match expected_left_source.")

    if any(
        item.source_type != expected_right_source for item in right
    ):
        raise ValueError("Right transactions do not match expected_right_source.")

    all_transactions = left + right
    transaction_ids = [item.transaction_id for item in all_transactions]

    if len(transaction_ids) != len(set(transaction_ids)):
        raise ValueError(
            "Missing detection input must contain unique transaction IDs."
        )

    classification_by_source = {
        SourceType.BANK: MissingClassification.MISSING_FROM_BANK,
        SourceType.LEDGER: MissingClassification.MISSING_FROM_LEDGER,
        SourceType.GATEWAY: MissingClassification.MISSING_FROM_GATEWAY,
    }

    findings = []

    for transaction in left:
        missing_source = expected_right_source
        findings.append(
            MissingEvidence(
                classification=classification_by_source[missing_source],
                transaction_id=transaction.transaction_id,
                transaction_source=transaction.source_type.value,
                missing_source=missing_source.value,
                reason=(
                    f"Transaction remains unmatched after the matching passes "
                    f"and has no selected counterpart in {missing_source.value}."
                ),
                compared_fields=("transaction_id", "source_type"),
                observed_values=(
                    ("transaction_id", transaction.transaction_id),
                    ("transaction_source", transaction.source_type.value),
                    ("missing_source", missing_source.value),
                ),
            )
        )

    for transaction in right:
        missing_source = expected_left_source
        findings.append(
            MissingEvidence(
                classification=classification_by_source[missing_source],
                transaction_id=transaction.transaction_id,
                transaction_source=transaction.source_type.value,
                missing_source=missing_source.value,
                reason=(
                    f"Transaction remains unmatched after the matching passes "
                    f"and has no selected counterpart in {missing_source.value}."
                ),
                compared_fields=("transaction_id", "source_type"),
                observed_values=(
                    ("transaction_id", transaction.transaction_id),
                    ("transaction_source", transaction.source_type.value),
                    ("missing_source", missing_source.value),
                ),
            )
        )

    return tuple(
        sorted(
            findings,
            key=lambda item: (
                item.missing_source,
                item.transaction_id,
            ),
        )
    )

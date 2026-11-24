"""Deterministic reconciliation status and financial total calculations."""

from collections import Counter, defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, Mapping

from app.models.enums import SourceType
from app.reconciliation.schemas import MatchOutcome, MatchingTransaction


def transaction_key(transaction: MatchingTransaction) -> str:
    """Return a source-qualified transaction identity."""
    return f"{transaction.source_type.value}:{transaction.transaction_id}"


@dataclass(frozen=True)
class TrackStatus:
    """Outcome counts and source totals for one independent reconciliation track."""

    track_name: str
    source_row_counts: Mapping[str, int]
    outcome_counts: Mapping[str, int]
    totals_by_source_currency: Mapping[str, Mapping[str, Decimal]]
    accounted_transaction_ids: Mapping[str, tuple[str, ...]]
    total_rows: int
    confirmed_count: int
    suggested_count: int
    ambiguous_count: int
    unmatched_count: int


@dataclass(frozen=True)
class ConsolidatedStatus:
    """Consolidated source totals without double-counting shared ledger rows."""

    source_row_counts: Mapping[str, int]
    totals_by_source_currency: Mapping[str, Mapping[str, Decimal]]
    unique_source_row_count: int
    track_statuses: Mapping[str, TrackStatus]


def calculate_track_status(
    *,
    track_name: str,
    left_transactions: Iterable[MatchingTransaction],
    right_transactions: Iterable[MatchingTransaction],
    outcomes: Mapping[str, MatchOutcome],
) -> TrackStatus:
    """Calculate one outcome for every source-qualified row in a track."""

    left = tuple(left_transactions)
    right = tuple(right_transactions)
    all_transactions = left + right

    keys = [transaction_key(item) for item in all_transactions]
    if len(keys) != len(set(keys)):
        raise ValueError("A transaction may occur only once within a track.")

    if set(outcomes) != set(keys):
        raise ValueError(
            "Every track transaction must have exactly one source-qualified outcome."
        )

    source_counts = Counter(item.source_type.value for item in all_transactions)
    outcome_counts = Counter(outcome.value for outcome in outcomes.values())

    totals: dict[str, dict[str, Decimal]] = defaultdict(
        lambda: defaultdict(Decimal)
    )
    ids_by_source: dict[str, list[str]] = defaultdict(list)

    for transaction in all_transactions:
        source = transaction.source_type.value
        totals[source][transaction.currency] += transaction.amount
        ids_by_source[source].append(transaction.transaction_id)

    ordered_totals = {
        source: dict(sorted(currency_totals.items()))
        for source, currency_totals in sorted(totals.items())
    }
    accounted = {
        source: tuple(sorted(ids))
        for source, ids in sorted(ids_by_source.items())
    }

    return TrackStatus(
        track_name=track_name,
        source_row_counts=dict(sorted(source_counts.items())),
        outcome_counts=dict(sorted(outcome_counts.items())),
        totals_by_source_currency=ordered_totals,
        accounted_transaction_ids=accounted,
        total_rows=len(all_transactions),
        confirmed_count=outcome_counts[MatchOutcome.CONFIRMED_AUTO.value],
        suggested_count=outcome_counts[MatchOutcome.SUGGESTED.value],
        ambiguous_count=outcome_counts[MatchOutcome.AMBIGUOUS.value],
        unmatched_count=outcome_counts[MatchOutcome.UNMATCHED.value],
    )


def calculate_consolidated_status(
    *,
    bank_transactions: Iterable[MatchingTransaction],
    ledger_transactions: Iterable[MatchingTransaction],
    gateway_transactions: Iterable[MatchingTransaction],
    track_statuses: Mapping[str, TrackStatus],
) -> ConsolidatedStatus:
    """Count each source row once, including shared ledger rows only once."""

    sources = {
        SourceType.BANK: tuple(bank_transactions),
        SourceType.LEDGER: tuple(ledger_transactions),
        SourceType.GATEWAY: tuple(gateway_transactions),
    }

    source_counts: dict[str, int] = {}
    totals: dict[str, dict[str, Decimal]] = {}
    all_keys: list[str] = []

    for source_type, transactions in sources.items():
        if any(item.source_type != source_type for item in transactions):
            raise ValueError(
                f"Transactions supplied for {source_type.value} contain "
                "an unexpected source type."
            )

        keys = [transaction_key(item) for item in transactions]
        if len(keys) != len(set(keys)):
            raise ValueError(
                f"{source_type.value} contains duplicate transaction identities."
            )

        source_counts[source_type.value] = len(transactions)
        currency_totals: dict[str, Decimal] = defaultdict(Decimal)

        for transaction in transactions:
            currency_totals[transaction.currency] += transaction.amount

        totals[source_type.value] = dict(sorted(currency_totals.items()))
        all_keys.extend(keys)

    if len(all_keys) != len(set(all_keys)):
        raise ValueError(
            "Source-qualified transaction identities must be unique."
        )

    return ConsolidatedStatus(
        source_row_counts=dict(sorted(source_counts.items())),
        totals_by_source_currency=dict(sorted(totals.items())),
        unique_source_row_count=len(all_keys),
        track_statuses=dict(sorted(track_statuses.items())),
    )

from datetime import timedelta
from decimal import Decimal
from typing import Iterable

from app.models.enums import SourceType
from app.reconciliation.rules import MatchingRuleset
from app.reconciliation.schemas import (
    MatchEvidence,
    MatchOutcome,
    MatchRule,
    MatchingResult,
    MatchingTransaction,
)


_SUPPORTED_SOURCE_PAIRS = {
    frozenset({SourceType.BANK, SourceType.LEDGER}),
    frozenset({SourceType.GATEWAY, SourceType.LEDGER}),
}


def _validate_transactions(
    transactions: tuple[MatchingTransaction, ...],
) -> None:
    """Validate canonical UTC dates and unique transaction IDs."""

    transaction_ids = [item.transaction_id for item in transactions]

    if len(transaction_ids) != len(set(transaction_ids)):
        raise ValueError("Aggregate matching cannot contain duplicate transaction IDs.")

    for transaction in transactions:
        value = transaction.transaction_date

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                "Aggregate matching requires timezone-aware UTC transaction dates."
            )

        if value.utcoffset() != timedelta(0):
            raise ValueError(
                "Transaction dates must be normalized to UTC before aggregate matching."
            )


def _evidence(
    ruleset: MatchingRuleset,
    reason: str,
    compared_fields: tuple[str, ...],
    observed_values: dict[str, str],
) -> MatchEvidence:
    return MatchEvidence(
        rule_id=MatchRule.AGGREGATE.value,
        rule_priority=ruleset.rule_priority.index("AGGREGATE"),
        reason=reason,
        compared_fields=compared_fields,
        observed_values=observed_values,
    )


def _result(
    transactions: tuple[MatchingTransaction, ...],
    ruleset: MatchingRuleset,
    outcome: MatchOutcome,
    evidence: MatchEvidence,
) -> MatchingResult:
    return MatchingResult(
        outcome=outcome,
        rule_id=MatchRule.AGGREGATE.value,
        transaction_ids=tuple(
            transaction.transaction_id for transaction in transactions
        ),
        evidence=(evidence,),
        ruleset_version=ruleset.version,
        ruleset_hash=ruleset.fingerprint,
    )


def _date_window(
    source_a: SourceType,
    source_b: SourceType,
    ruleset: MatchingRuleset,
) -> int:
    sources = frozenset({source_a, source_b})

    if sources == frozenset({SourceType.BANK, SourceType.LEDGER}):
        return ruleset.bank_ledger_date_window_days

    if sources == frozenset({SourceType.GATEWAY, SourceType.LEDGER}):
        return ruleset.gateway_ledger_date_window_days

    raise ValueError("Unsupported transaction source combination.")


def match_aggregate_group(
    left_transactions: Iterable[MatchingTransaction],
    right_transactions: Iterable[MatchingTransaction],
    ruleset: MatchingRuleset,
) -> MatchingResult:
    """
    Evaluate an explicit one-to-many or many-to-one aggregate candidate.

    Exactly one side must contain one transaction. The other side must
    contain between two and aggregate_max_group_size transactions.

    The aggregate side must contain transactions from one source type.
    The singleton side must contain the other supported source type.

    A candidate is SUGGESTED only when:
    - The source combination is BANK–LEDGER or GATEWAY–LEDGER.
    - Transaction IDs are unique.
    - All transaction dates are timezone-aware UTC.
    - All transactions use the same currency.
    - Every grouped transaction is within the configured date window
      of the singleton transaction.
    - The exact Decimal group total equals the singleton amount.

    Aggregate matching never automatically confirms a financial match.
    It does not persist results or approve financial actions.
    """

    left = tuple(left_transactions)
    right = tuple(right_transactions)

    if not left or not right:
        raise ValueError("Both sides must contain at least one transaction.")

    if len(left) != 1 and len(right) != 1:
        raise ValueError(
            "Aggregate matching requires exactly one transaction on one side."
        )

    if len(left) == 1 and len(right) == 1:
        raise ValueError(
            "Aggregate matching requires at least two transactions on the grouped side."
        )

    singleton = left[0] if len(left) == 1 else right[0]
    grouped = right if len(left) == 1 else left

    if len(left) + len(right) > ruleset.aggregate_max_group_size:
        raise ValueError(
            "Aggregate group exceeds the configured maximum group size."
        )

    all_transactions = left + right
    _validate_transactions(all_transactions)

    grouped_sources = {transaction.source_type for transaction in grouped}

    if len(grouped_sources) != 1:
        raise ValueError(
            "All transactions in an aggregate group must have the same source type."
        )

    grouped_source = next(iter(grouped_sources))
    source_pair = frozenset({singleton.source_type, grouped_source})

    if source_pair not in _SUPPORTED_SOURCE_PAIRS:
        evidence = _evidence(
            ruleset,
            "The source combination is not supported for aggregate matching.",
            ("source_type",),
            {
                "singleton_source": singleton.source_type.value,
                "grouped_source": grouped_source.value,
            },
        )
        return _result(
            all_transactions,
            ruleset,
            MatchOutcome.UNMATCHED,
            evidence,
        )

    currencies = {transaction.currency for transaction in all_transactions}

    if len(currencies) != 1:
        evidence = _evidence(
            ruleset,
            "Currency mismatch; aggregate amounts cannot be compared.",
            ("currency",),
            {
                "currencies": ", ".join(sorted(currencies)),
            },
        )
        return _result(
            all_transactions,
            ruleset,
            MatchOutcome.UNMATCHED,
            evidence,
        )

    allowed_days = _date_window(
        singleton.source_type,
        grouped_source,
        ruleset,
    )

    date_differences = [
        abs(
            (
                transaction.transaction_date.date()
                - singleton.transaction_date.date()
            ).days
        )
        for transaction in grouped
    ]

    maximum_date_difference = max(date_differences)

    if maximum_date_difference > allowed_days:
        evidence = _evidence(
            ruleset,
            "At least one grouped transaction falls outside the configured date window.",
            ("transaction_date",),
            {
                "singleton_date": singleton.transaction_date.date().isoformat(),
                "grouped_dates": ", ".join(
                    transaction.transaction_date.date().isoformat()
                    for transaction in grouped
                ),
                "maximum_date_difference_days": str(maximum_date_difference),
                "allowed_date_window_days": str(allowed_days),
            },
        )
        return _result(
            all_transactions,
            ruleset,
            MatchOutcome.UNMATCHED,
            evidence,
        )

    grouped_total = sum(
        (transaction.amount for transaction in grouped),
        Decimal("0"),
    )

    singleton_amount = singleton.amount

    observed_values = {
        "singleton_transaction_id": singleton.transaction_id,
        "grouped_transaction_ids": ", ".join(
            transaction.transaction_id for transaction in grouped
        ),
        "singleton_amount": str(singleton_amount),
        "grouped_total": str(grouped_total),
        "amount_difference": str(abs(singleton_amount - grouped_total)),
        "currency": singleton.currency,
        "singleton_source": singleton.source_type.value,
        "grouped_source": grouped_source.value,
        "singleton_date": singleton.transaction_date.date().isoformat(),
        "maximum_date_difference_days": str(maximum_date_difference),
        "allowed_date_window_days": str(allowed_days),
        "group_size": str(len(grouped)),
        "maximum_group_size": str(ruleset.aggregate_max_group_size),
    }

    compared_fields = (
        "transaction_ids",
        "amount",
        "currency",
        "transaction_date",
        "source_type",
    )

    if grouped_total != singleton_amount:
        evidence = _evidence(
            ruleset,
            "The grouped Decimal total does not equal the singleton transaction amount.",
            compared_fields,
            observed_values,
        )
        return _result(
            all_transactions,
            ruleset,
            MatchOutcome.UNMATCHED,
            evidence,
        )

    evidence = _evidence(
        ruleset,
        "The grouped Decimal total equals the singleton amount, currencies match, "
        "and all grouped dates are within the configured window. "
        "This is a review candidate, not an approved financial match.",
        compared_fields,
        observed_values,
    )

    return _result(
        all_transactions,
        ruleset,
        MatchOutcome.SUGGESTED,
        evidence,
    )

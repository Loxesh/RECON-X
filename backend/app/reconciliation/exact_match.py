
from datetime import datetime, timedelta
from decimal import Decimal

from app.models.enums import SourceType
from app.reconciliation.rules import MatchingRuleset
from app.reconciliation.schemas import (
    MatchEvidence,
    MatchOutcome,
    MatchingPairInput,
    MatchingResult,
    MatchRule,
)


_SUPPORTED_SOURCE_PAIRS = {
    frozenset({SourceType.BANK, SourceType.LEDGER}),
    frozenset({SourceType.GATEWAY, SourceType.LEDGER}),
}


def _date_only(value: datetime):
    """Return the calendar date of a canonical UTC datetime."""
    return value.date()


def _validate_utc_dates(pair: MatchingPairInput) -> None:
    """Reject transaction dates that violate the canonical UTC contract."""

    for transaction in (pair.left, pair.right):
        value = transaction.transaction_date

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                "Matching requires timezone-aware UTC transaction dates."
            )

        if value.utcoffset() != timedelta(0):
            raise ValueError(
                "Transaction dates must be normalized to UTC before matching."
            )


def _date_window(
    left_source: SourceType,
    right_source: SourceType,
    ruleset: MatchingRuleset,
) -> int:
    """Return the configured date window for a supported source pair."""
    sources = frozenset({left_source, right_source})

    if sources == frozenset({SourceType.BANK, SourceType.LEDGER}):
        return ruleset.bank_ledger_date_window_days

    if sources == frozenset({SourceType.GATEWAY, SourceType.LEDGER}):
        return ruleset.gateway_ledger_date_window_days

    raise ValueError("Unsupported transaction source combination.")


def _priority(ruleset: MatchingRuleset, rule_name: str) -> int:
    """Return the configured zero-based priority of a matching rule."""
    return ruleset.rule_priority.index(rule_name)


def _evidence(
    ruleset: MatchingRuleset,
    rule_name: str,
    reason: str,
    compared_fields: tuple[str, ...],
    observed_values: dict[str, str],
) -> MatchEvidence:
    rule_id = (
        MatchRule.EXACT.value
        if rule_name == "EXACT"
        else MatchRule.REFERENCE.value
    )

    return MatchEvidence(
        rule_id=rule_id,
        rule_priority=_priority(ruleset, rule_name),
        reason=reason,
        compared_fields=compared_fields,
        observed_values=observed_values,
    )


def _result(
    pair: MatchingPairInput,
    ruleset: MatchingRuleset,
    outcome: MatchOutcome,
    evidence: list[MatchEvidence],
    rule_id: str | None = None,
) -> MatchingResult:
    return MatchingResult(
        outcome=outcome,
        rule_id=rule_id,
        transaction_ids=(
            pair.left.transaction_id,
            pair.right.transaction_id,
        ),
        evidence=tuple(evidence),
        ruleset_version=ruleset.version,
        ruleset_hash=ruleset.fingerprint,
    )


def match_exact_pair(
    pair: MatchingPairInput,
    ruleset: MatchingRuleset,
) -> MatchingResult:
    """
    Deterministically compare two canonical transactions.

    Supported passes:
    - EXACT_01: Same transaction ID, amount, currency and calendar date.
    - REF_01: Same normalized reference and amount, same currency,
      and within the configured source-specific date window.

    Transaction dates must be timezone-aware UTC datetimes.

    This function does not persist results or approve financial actions.
    """

    if (
        pair.ruleset_version != ruleset.version
        or pair.ruleset_hash != ruleset.fingerprint
    ):
        raise ValueError(
            "Matching pair ruleset identity does not match the supplied ruleset."
        )

    # Enforce the canonical UTC date contract before comparing dates.
    _validate_utc_dates(pair)

    left = pair.left
    right = pair.right

    evidence: list[MatchEvidence] = []

    source_pair = frozenset({left.source_type, right.source_type})

    if source_pair not in _SUPPORTED_SOURCE_PAIRS:
        evidence.append(
            _evidence(
                ruleset,
                "EXACT",
                "The source combination is not supported for cross-source matching.",
                ("source_type",),
                {
                    "left_source": left.source_type.value,
                    "right_source": right.source_type.value,
                },
            )
        )
        return _result(
            pair, ruleset, MatchOutcome.UNMATCHED, evidence
        )

    # Financial amounts must be compared only in the same currency.
    if left.currency != right.currency:
        evidence.append(
            _evidence(
                ruleset,
                "EXACT",
                "Currency mismatch; amounts cannot be compared.",
                ("currency",),
                {
                    "left_currency": left.currency,
                    "right_currency": right.currency,
                },
            )
        )
        return _result(
            pair, ruleset, MatchOutcome.UNMATCHED, evidence
        )

    amount_equal = left.amount == right.amount
    same_date = _date_only(left.transaction_date) == _date_only(
        right.transaction_date
    )

    # Evaluate only the exact ID and reference passes in configured order.
    passes = sorted(
        ("EXACT", "REFERENCE"),
        key=lambda name: _priority(ruleset, name),
    )

    for pass_name in passes:

        if pass_name == "EXACT":
            if left.transaction_id != right.transaction_id:
                continue

            if amount_equal and same_date:
                evidence.append(
                    _evidence(
                        ruleset,
                        "EXACT",
                        "Transaction ID, amount, currency and date agree exactly.",
                        (
                            "transaction_id",
                            "amount",
                            "currency",
                            "transaction_date",
                        ),
                        {
                            "transaction_id": left.transaction_id,
                            "amount": str(left.amount),
                            "currency": left.currency,
                            "transaction_date": _date_only(
                                left.transaction_date
                            ).isoformat(),
                        },
                    )
                )

                return _result(
                    pair,
                    ruleset,
                    MatchOutcome.CONFIRMED_AUTO,
                    evidence,
                    MatchRule.EXACT.value,
                )

            failed_checks = []

            if not amount_equal:
                failed_checks.append("amount")

            if not same_date:
                failed_checks.append("transaction date")

            evidence.append(
                _evidence(
                    ruleset,
                    "EXACT",
                    "Transaction IDs agree, but exact constraints failed: "
                    + ", ".join(failed_checks),
                    (
                        "transaction_id",
                        "amount",
                        "currency",
                        "transaction_date",
                    ),
                    {
                        "transaction_id": left.transaction_id,
                        "left_amount": str(left.amount),
                        "right_amount": str(right.amount),
                        "left_date": _date_only(
                            left.transaction_date
                        ).isoformat(),
                        "right_date": _date_only(
                            right.transaction_date
                        ).isoformat(),
                    },
                )
            )

        elif pass_name == "REFERENCE":
            left_reference = left.reference_norm
            right_reference = right.reference_norm

            if (
                not left_reference
                or not right_reference
                or left_reference != right_reference
            ):
                continue

            date_difference = abs(
                (
                    _date_only(left.transaction_date)
                    - _date_only(right.transaction_date)
                ).days
            )

            allowed_days = _date_window(
                left.source_type,
                right.source_type,
                ruleset,
            )

            if not amount_equal:
                evidence.append(
                    _evidence(
                        ruleset,
                        "REFERENCE",
                        "References agree, but transaction amounts differ.",
                        ("reference_norm", "amount"),
                        {
                            "reference": left_reference,
                            "left_amount": str(left.amount),
                            "right_amount": str(right.amount),
                        },
                    )
                )
                continue

            if date_difference > allowed_days:
                evidence.append(
                    _evidence(
                        ruleset,
                        "REFERENCE",
                        "References and amounts agree, but the date difference "
                        "exceeds the configured window.",
                        ("reference_norm", "amount", "transaction_date"),
                        {
                            "reference": left_reference,
                            "date_difference_days": str(date_difference),
                            "allowed_date_window_days": str(allowed_days),
                        },
                    )
                )
                continue

            evidence.append(
                _evidence(
                    ruleset,
                    "REFERENCE",
                    "Normalized reference and amount agree, currency matches, "
                    "and transaction dates are within the configured window.",
                    (
                        "reference_norm",
                        "amount",
                        "currency",
                        "transaction_date",
                    ),
                    {
                        "reference": left_reference,
                        "amount": str(left.amount),
                        "currency": left.currency,
                        "date_difference_days": str(date_difference),
                        "allowed_date_window_days": str(allowed_days),
                    },
                )
            )

            return _result(
                pair,
                ruleset,
                MatchOutcome.CONFIRMED_AUTO,
                evidence,
                MatchRule.REFERENCE.value,
            )

    if not evidence:
        evidence.append(
            _evidence(
                ruleset,
                "REFERENCE",
                "No exact transaction ID or normalized reference match was found.",
                ("transaction_id", "reference_norm"),
                {
                    "left_transaction_id": left.transaction_id,
                    "right_transaction_id": right.transaction_id,
                    "left_reference": left.reference_norm or "",
                    "right_reference": right.reference_norm or "",
                },
            )
        )

    return _result(
        pair,
        ruleset,
        MatchOutcome.UNMATCHED,
        evidence,
    )

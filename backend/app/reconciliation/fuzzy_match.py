
from datetime import timedelta
from decimal import Decimal
from typing import Iterable

from rapidfuzz import fuzz

from app.models.enums import SourceType
from app.reconciliation.rules import MatchingRuleset
from app.reconciliation.schemas import (
    MatchEvidence,
    MatchOutcome,
    MatchingPairInput,
    MatchingResult,
    MatchRule,
    MatchingTransaction,
)

_SUPPORTED_SOURCE_PAIRS = {
    frozenset({SourceType.BANK, SourceType.LEDGER}),
    frozenset({SourceType.GATEWAY, SourceType.LEDGER}),
}

_SCORE_QUANTUM = Decimal("0.0001")


def _validate_utc_dates(pair: MatchingPairInput) -> None:
    for transaction in (pair.left, pair.right):
        value = transaction.transaction_date
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                "Fuzzy matching requires timezone-aware UTC transaction dates."
            )
        if value.utcoffset() != timedelta(0):
            raise ValueError(
                "Transaction dates must be normalized to UTC before fuzzy matching."
            )


def _validate_ruleset(
    pair: MatchingPairInput,
    ruleset: MatchingRuleset,
) -> None:
    if (
        pair.ruleset_version != ruleset.version
        or pair.ruleset_hash != ruleset.fingerprint
    ):
        raise ValueError(
            "Matching pair ruleset identity does not match the supplied ruleset."
        )


def _date_window(
    left_source: SourceType,
    right_source: SourceType,
    ruleset: MatchingRuleset,
) -> int:
    sources = frozenset({left_source, right_source})

    if sources == frozenset({SourceType.BANK, SourceType.LEDGER}):
        return ruleset.bank_ledger_date_window_days

    if sources == frozenset({SourceType.GATEWAY, SourceType.LEDGER}):
        return ruleset.gateway_ledger_date_window_days

    raise ValueError("Unsupported transaction source combination.")


def _normalize_reference(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.casefold().split())


def _similarity_score(left: str, right: str) -> Decimal:
    raw_score = fuzz.ratio(left, right)
    return (Decimal(str(raw_score)) / Decimal("100")).quantize(
        _SCORE_QUANTUM
    )


def _evidence(
    ruleset: MatchingRuleset,
    reason: str,
    compared_fields: tuple[str, ...],
    observed_values: dict[str, str],
) -> MatchEvidence:
    return MatchEvidence(
        rule_id=MatchRule.FUZZY.value,
        rule_priority=ruleset.rule_priority.index("FUZZY"),
        reason=reason,
        compared_fields=compared_fields,
        observed_values=observed_values,
    )


def _result(
    pair: MatchingPairInput,
    ruleset: MatchingRuleset,
    outcome: MatchOutcome,
    evidence: MatchEvidence,
    candidate_score: Decimal | None = None,
) -> MatchingResult:
    return MatchingResult(
        outcome=outcome,
        rule_id=MatchRule.FUZZY.value if candidate_score is not None else None,
        transaction_ids=(
            pair.left.transaction_id,
            pair.right.transaction_id,
        ),
        evidence=(evidence,),
        candidate_score=candidate_score,
        ruleset_version=ruleset.version,
        ruleset_hash=ruleset.fingerprint,
    )


def match_fuzzy_pair(
    pair: MatchingPairInput,
    ruleset: MatchingRuleset,
) -> MatchingResult:
    """Evaluate reference similarity as a non-confirming fuzzy candidate."""

    _validate_ruleset(pair, ruleset)
    _validate_utc_dates(pair)

    left = pair.left
    right = pair.right
    source_pair = frozenset({left.source_type, right.source_type})

    if source_pair not in _SUPPORTED_SOURCE_PAIRS:
        evidence = _evidence(
            ruleset,
            "The source combination is not supported for fuzzy matching.",
            ("source_type",),
            {
                "left_source": left.source_type.value,
                "right_source": right.source_type.value,
            },
        )
        return _result(pair, ruleset, MatchOutcome.UNMATCHED, evidence)

    if left.transaction_id == right.transaction_id:
        evidence = _evidence(
            ruleset,
            "Identical transaction IDs must be evaluated by earlier matching passes.",
            ("transaction_id",),
            {"transaction_id": left.transaction_id},
        )
        return _result(pair, ruleset, MatchOutcome.UNMATCHED, evidence)

    if left.currency != right.currency:
        evidence = _evidence(
            ruleset,
            "Currency mismatch; fuzzy financial candidates cannot compare unlike currencies.",
            ("currency",),
            {
                "left_currency": left.currency,
                "right_currency": right.currency,
            },
        )
        return _result(pair, ruleset, MatchOutcome.UNMATCHED, evidence)

    amount_difference = abs(left.amount - right.amount)
    if amount_difference > ruleset.suggested_amount_tolerance:
        evidence = _evidence(
            ruleset,
            "Amount difference exceeds the configured suggested tolerance.",
            ("amount",),
            {
                "left_amount": str(left.amount),
                "right_amount": str(right.amount),
                "amount_difference": str(amount_difference),
                "allowed_tolerance": str(ruleset.suggested_amount_tolerance),
            },
        )
        return _result(pair, ruleset, MatchOutcome.UNMATCHED, evidence)

    left_date = left.transaction_date.date()
    right_date = right.transaction_date.date()
    date_difference = abs((left_date - right_date).days)

    allowed_days = _date_window(
        left.source_type,
        right.source_type,
        ruleset,
    )

    if date_difference > allowed_days:
        evidence = _evidence(
            ruleset,
            "Transaction date difference exceeds the configured source-specific window.",
            ("transaction_date",),
            {
                "left_date": left_date.isoformat(),
                "right_date": right_date.isoformat(),
                "date_difference_days": str(date_difference),
                "allowed_date_window_days": str(allowed_days),
            },
        )
        return _result(pair, ruleset, MatchOutcome.UNMATCHED, evidence)

    left_reference = _normalize_reference(left.reference_norm)
    right_reference = _normalize_reference(right.reference_norm)

    if not left_reference or not right_reference:
        evidence = _evidence(
            ruleset,
            "Fuzzy matching requires both normalized transaction references.",
            ("reference_norm",),
            {
                "left_reference_present": str(bool(left_reference)),
                "right_reference_present": str(bool(right_reference)),
            },
        )
        return _result(pair, ruleset, MatchOutcome.UNMATCHED, evidence)

    score = _similarity_score(left_reference, right_reference)

    observed_values = {
        "left_reference": left_reference,
        "right_reference": right_reference,
        "similarity_score": str(score),
        "fuzzy_threshold": str(ruleset.fuzzy_threshold),
        "left_amount": str(left.amount),
        "right_amount": str(right.amount),
        "amount_difference": str(amount_difference),
        "allowed_amount_tolerance": str(ruleset.suggested_amount_tolerance),
        "date_difference_days": str(date_difference),
        "allowed_date_window_days": str(allowed_days),
        "currency": left.currency,
    }

    compared_fields = (
        "reference_norm",
        "amount",
        "currency",
        "transaction_date",
    )

    if score < ruleset.fuzzy_threshold:
        evidence = _evidence(
            ruleset,
            "Reference similarity is below the configured fuzzy threshold.",
            compared_fields,
            observed_values,
        )
        return _result(
            pair,
            ruleset,
            MatchOutcome.UNMATCHED,
            evidence,
            candidate_score=score,
        )

    evidence = _evidence(
        ruleset,
        "Reference similarity meets the configured threshold and financial/date "
        "constraints are satisfied. This is a review candidate, not an approved match.",
        compared_fields,
        observed_values,
    )

    return _result(
        pair,
        ruleset,
        MatchOutcome.SUGGESTED,
        evidence,
        candidate_score=score,
    )


def match_fuzzy_candidates(
    transaction: MatchingTransaction,
    candidates: Iterable[MatchingTransaction],
    ruleset: MatchingRuleset,
) -> tuple[MatchingResult, ...]:
    """Evaluate candidates and deterministically identify top-score ambiguity."""

    results = []

    for candidate in candidates:
        pair = MatchingPairInput(
            left=transaction,
            right=candidate,
            ruleset_version=ruleset.version,
            ruleset_hash=ruleset.fingerprint,
        )
        result = match_fuzzy_pair(pair, ruleset)

        if result.outcome == MatchOutcome.SUGGESTED:
            results.append(result)

    results.sort(
        key=lambda result: (
            -(result.candidate_score or Decimal("0")),
            result.transaction_ids,
        )
    )

    if not results:
        return ()

    highest_score = results[0].candidate_score
    tied_highest = [
        result for result in results
        if result.candidate_score == highest_score
    ]

    if len(tied_highest) <= 1:
        return tuple(results)

    ambiguous_ids = {
        result.transaction_ids for result in tied_highest
    }

    updated_results = []

    for result in results:
        if result.transaction_ids in ambiguous_ids:
            updated_evidence = result.evidence[0].model_copy(
                update={
                    "reason": (
                        result.evidence[0].reason
                        + " Multiple candidates share the highest similarity "
                        "score; human review is required."
                    )
                }
            )
            result = result.model_copy(
                update={
                    "outcome": MatchOutcome.AMBIGUOUS,
                    "evidence": (updated_evidence,),
                }
            )

        updated_results.append(result)

    return tuple(updated_results)

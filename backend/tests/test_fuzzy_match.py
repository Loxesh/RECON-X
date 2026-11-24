
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.models.enums import SourceType
from app.reconciliation.fuzzy_match import (
    match_fuzzy_candidates,
    match_fuzzy_pair,
)
from app.reconciliation.rules import MatchingRuleset
from app.reconciliation.schemas import (
    MatchOutcome,
    MatchingPairInput,
    MatchingTransaction,
)


@pytest.fixture
def rules():
    return MatchingRuleset()


def make_transaction(
    transaction_id,
    source,
    *,
    reference="INV-2026-1001",
    description="monthly subscription payment",
    amount="100.00",
    currency="INR",
    date=None,
):
    return MatchingTransaction(
        transaction_id=transaction_id,
        source_type=source,
        transaction_reference=reference,
        reference_norm=reference,
        transaction_date=date or datetime(
            2026, 11, 20, tzinfo=timezone.utc
        ),
        amount=Decimal(amount),
        currency=currency,
        fingerprint=f"fingerprint-{transaction_id}",
        description_norm=description,
    )


def make_pair(left, right, rules):
    return MatchingPairInput(
        left=left,
        right=right,
        ruleset_version=rules.version,
        ruleset_hash=rules.fingerprint,
    )


def test_typographical_reference_difference_produces_suggestion(rules):
    left = make_transaction("BANK-001", SourceType.BANK)
    right = make_transaction(
        "LEDGER-001",
        SourceType.LEDGER,
        reference="INV-2026-100I",
        description="completely different description",
        amount="100.50",
    )

    result = match_fuzzy_pair(make_pair(left, right, rules), rules)

    assert result.outcome == MatchOutcome.SUGGESTED
    assert result.rule_id == "FUZZY_01"
    assert result.candidate_score >= rules.fuzzy_threshold


def test_fuzzy_candidate_is_never_auto_confirmed(rules):
    left = make_transaction("BANK-001", SourceType.BANK)
    right = make_transaction(
        "LEDGER-001",
        SourceType.LEDGER,
        reference="INV-2026-100I",
    )

    result = match_fuzzy_pair(make_pair(left, right, rules), rules)

    assert result.outcome == MatchOutcome.SUGGESTED
    assert result.outcome != MatchOutcome.CONFIRMED_AUTO


def test_amount_difference_within_tolerance_is_allowed(rules):
    left = make_transaction("BANK-001", SourceType.BANK)
    right = make_transaction(
        "LEDGER-001", SourceType.LEDGER, amount="101.00"
    )

    result = match_fuzzy_pair(make_pair(left, right, rules), rules)
    assert result.outcome == MatchOutcome.SUGGESTED


def test_amount_difference_above_tolerance_is_rejected(rules):
    left = make_transaction("BANK-001", SourceType.BANK)
    right = make_transaction(
        "LEDGER-001", SourceType.LEDGER, amount="101.01"
    )

    result = match_fuzzy_pair(make_pair(left, right, rules), rules)
    assert result.outcome == MatchOutcome.UNMATCHED


def test_bank_ledger_date_inside_window_is_allowed(rules):
    left = make_transaction("BANK-001", SourceType.BANK)
    right = make_transaction(
        "LEDGER-001",
        SourceType.LEDGER,
        date=datetime(2026, 11, 22, tzinfo=timezone.utc),
    )

    result = match_fuzzy_pair(make_pair(left, right, rules), rules)
    assert result.outcome == MatchOutcome.SUGGESTED


def test_bank_ledger_date_outside_window_is_rejected(rules):
    left = make_transaction("BANK-001", SourceType.BANK)
    right = make_transaction(
        "LEDGER-001",
        SourceType.LEDGER,
        date=datetime(2026, 11, 23, tzinfo=timezone.utc),
    )

    result = match_fuzzy_pair(make_pair(left, right, rules), rules)
    assert result.outcome == MatchOutcome.UNMATCHED


def test_gateway_ledger_uses_configured_three_day_window(rules):
    left = make_transaction("GW-001", SourceType.GATEWAY)
    right = make_transaction(
        "LEDGER-001",
        SourceType.LEDGER,
        date=datetime(2026, 11, 23, tzinfo=timezone.utc),
    )

    result = match_fuzzy_pair(make_pair(left, right, rules), rules)
    assert result.outcome == MatchOutcome.SUGGESTED


def test_currency_mismatch_is_rejected(rules):
    left = make_transaction("BANK-001", SourceType.BANK, currency="INR")
    right = make_transaction("LEDGER-001", SourceType.LEDGER, currency="USD")

    result = match_fuzzy_pair(make_pair(left, right, rules), rules)
    assert result.outcome == MatchOutcome.UNMATCHED


def test_missing_reference_is_rejected(rules):
    left = make_transaction("BANK-001", SourceType.BANK, reference=None)
    right = make_transaction("LEDGER-001", SourceType.LEDGER)

    result = match_fuzzy_pair(make_pair(left, right, rules), rules)
    assert result.outcome == MatchOutcome.UNMATCHED


def test_identical_transaction_id_is_not_fuzzy_matched(rules):
    left = make_transaction("TXN-001", SourceType.BANK)
    right = make_transaction("TXN-001", SourceType.LEDGER)

    result = match_fuzzy_pair(make_pair(left, right, rules), rules)
    assert result.outcome == MatchOutcome.UNMATCHED


def test_unsupported_source_pair_is_rejected(rules):
    left = make_transaction("BANK-001", SourceType.BANK)
    right = make_transaction("GW-001", SourceType.GATEWAY)

    result = match_fuzzy_pair(make_pair(left, right, rules), rules)
    assert result.outcome == MatchOutcome.UNMATCHED


def test_naive_datetime_is_rejected(rules):
    left = make_transaction(
        "BANK-001",
        SourceType.BANK,
        date=datetime(2026, 11, 20),
    )
    right = make_transaction("LEDGER-001", SourceType.LEDGER)

    with pytest.raises(ValueError, match="timezone-aware UTC"):
        match_fuzzy_pair(make_pair(left, right, rules), rules)


def test_non_utc_datetime_is_rejected(rules):
    non_utc = timezone(timedelta(hours=5, minutes=30))
    left = make_transaction(
        "BANK-001",
        SourceType.BANK,
        date=datetime(2026, 11, 20, tzinfo=non_utc),
    )
    right = make_transaction("LEDGER-001", SourceType.LEDGER)

    with pytest.raises(ValueError, match="normalized to UTC"):
        match_fuzzy_pair(make_pair(left, right, rules), rules)


def test_ruleset_identity_mismatch_is_rejected(rules):
    left = make_transaction("BANK-001", SourceType.BANK)
    right = make_transaction("LEDGER-001", SourceType.LEDGER)

    pair = MatchingPairInput(
        left=left,
        right=right,
        ruleset_version="2.0.0",
        ruleset_hash=rules.fingerprint,
    )

    with pytest.raises(ValueError, match="ruleset identity"):
        match_fuzzy_pair(pair, rules)


def test_candidate_collection_marks_equal_top_scores_ambiguous(rules):
    anchor = make_transaction("BANK-001", SourceType.BANK)
    first = make_transaction("LEDGER-001", SourceType.LEDGER)
    second = make_transaction("LEDGER-002", SourceType.LEDGER)

    results = match_fuzzy_candidates(anchor, [first, second], rules)

    assert len(results) == 2
    assert all(result.outcome == MatchOutcome.AMBIGUOUS for result in results)


def test_candidate_collection_returns_deterministic_order(rules):
    anchor = make_transaction("BANK-001", SourceType.BANK)
    first = make_transaction(
        "LEDGER-002",
        SourceType.LEDGER,
        reference="INV-2026-100I",
    )
    second = make_transaction("LEDGER-001", SourceType.LEDGER)

    first_run = match_fuzzy_candidates(anchor, [first, second], rules)
    second_run = match_fuzzy_candidates(anchor, [second, first], rules)

    assert [r.model_dump() for r in first_run] == [
        r.model_dump() for r in second_run
    ]


def test_no_qualifying_candidate_returns_empty_tuple(rules):
    anchor = make_transaction("BANK-001", SourceType.BANK)
    candidate = make_transaction(
        "LEDGER-001",
        SourceType.LEDGER,
        reference="ELECTRICITY-778",
    )

    results = match_fuzzy_candidates(anchor, [candidate], rules)
    assert results == ()


def test_fuzzy_result_preserves_ruleset_identity(rules):
    left = make_transaction("BANK-001", SourceType.BANK)
    right = make_transaction(
        "LEDGER-001",
        SourceType.LEDGER,
        reference="INV-2026-100I",
    )

    result = match_fuzzy_pair(make_pair(left, right, rules), rules)

    assert result.ruleset_version == rules.version
    assert result.ruleset_hash == rules.fingerprint


def test_fuzzy_result_contains_reference_evidence(rules):
    left = make_transaction("BANK-001", SourceType.BANK)
    right = make_transaction(
        "LEDGER-001",
        SourceType.LEDGER,
        reference="INV-2026-100I",
    )

    result = match_fuzzy_pair(make_pair(left, right, rules), rules)

    assert result.evidence
    assert result.evidence[0].rule_id == "FUZZY_01"
    assert "similarity_score" in result.evidence[0].observed_values
    assert "left_reference" in result.evidence[0].observed_values

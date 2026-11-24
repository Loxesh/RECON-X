
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.models.enums import SourceType
from app.reconciliation.exact_match import match_exact_pair
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
    reference="REF-100",
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
        description_norm="payment",
    )


def make_pair(left, right, rules):
    return MatchingPairInput(
        left=left,
        right=right,
        ruleset_version=rules.version,
        ruleset_hash=rules.fingerprint,
    )


def test_exact_transaction_id_match(rules):
    left = make_transaction("TXN-001", SourceType.BANK)
    right = make_transaction("TXN-001", SourceType.LEDGER)

    result = match_exact_pair(make_pair(left, right, rules), rules)

    assert result.outcome == MatchOutcome.CONFIRMED_AUTO
    assert result.rule_id == "EXACT_01"
    assert len(result.evidence) == 1


def test_reference_match_within_bank_ledger_window(rules):
    left = make_transaction("BANK-001", SourceType.BANK)

    right = make_transaction(
        "LEDGER-001",
        SourceType.LEDGER,
        date=datetime(2026, 11, 22, tzinfo=timezone.utc),
    )

    result = match_exact_pair(make_pair(left, right, rules), rules)

    assert result.outcome == MatchOutcome.CONFIRMED_AUTO
    assert result.rule_id == "REF_01"


def test_reference_match_outside_bank_ledger_window(rules):
    left = make_transaction("BANK-001", SourceType.BANK)

    right = make_transaction(
        "LEDGER-001",
        SourceType.LEDGER,
        date=datetime(2026, 11, 23, tzinfo=timezone.utc),
    )

    result = match_exact_pair(make_pair(left, right, rules), rules)

    assert result.outcome == MatchOutcome.UNMATCHED


def test_gateway_ledger_uses_three_day_window(rules):
    left = make_transaction("GW-001", SourceType.GATEWAY)

    right = make_transaction(
        "LEDGER-001",
        SourceType.LEDGER,
        date=datetime(2026, 11, 23, tzinfo=timezone.utc),
    )

    result = match_exact_pair(make_pair(left, right, rules), rules)

    assert result.outcome == MatchOutcome.CONFIRMED_AUTO
    assert result.rule_id == "REF_01"


def test_amount_mismatch_is_not_confirmed(rules):
    left = make_transaction("BANK-001", SourceType.BANK)

    right = make_transaction(
        "LEDGER-001",
        SourceType.LEDGER,
        amount="101.00",
    )

    result = match_exact_pair(make_pair(left, right, rules), rules)

    assert result.outcome == MatchOutcome.UNMATCHED


def test_currency_mismatch_is_not_compared(rules):
    left = make_transaction("BANK-001", SourceType.BANK)

    right = make_transaction(
        "LEDGER-001",
        SourceType.LEDGER,
        currency="USD",
    )

    result = match_exact_pair(make_pair(left, right, rules), rules)

    assert result.outcome == MatchOutcome.UNMATCHED
    assert "Currency mismatch" in result.evidence[0].reason


def test_reference_mismatch_is_not_confirmed(rules):
    left = make_transaction(
        "BANK-001", SourceType.BANK, reference="REF-100"
    )

    right = make_transaction(
        "LEDGER-001", SourceType.LEDGER, reference="REF-200"
    )

    result = match_exact_pair(make_pair(left, right, rules), rules)

    assert result.outcome == MatchOutcome.UNMATCHED


def test_missing_reference_is_not_matched(rules):
    left = make_transaction(
        "BANK-001", SourceType.BANK, reference=None
    )

    right = make_transaction(
        "LEDGER-001", SourceType.LEDGER, reference=None
    )

    result = match_exact_pair(make_pair(left, right, rules), rules)

    assert result.outcome == MatchOutcome.UNMATCHED


def test_same_source_pair_is_not_supported(rules):
    left = make_transaction("BANK-001", SourceType.BANK)
    right = make_transaction("BANK-002", SourceType.BANK)

    result = match_exact_pair(make_pair(left, right, rules), rules)

    assert result.outcome == MatchOutcome.UNMATCHED
    assert "not supported" in result.evidence[0].reason


def test_bank_gateway_pair_is_not_supported(rules):
    left = make_transaction("BANK-001", SourceType.BANK)
    right = make_transaction("GW-001", SourceType.GATEWAY)

    result = match_exact_pair(make_pair(left, right, rules), rules)

    assert result.outcome == MatchOutcome.UNMATCHED


def test_exact_id_requires_same_date(rules):
    left = make_transaction("TXN-001", SourceType.BANK)

    right = make_transaction(
        "TXN-001",
        SourceType.LEDGER,
        reference="REF-OTHER",
        date=datetime(2026, 11, 21, tzinfo=timezone.utc),
    )

    result = match_exact_pair(make_pair(left, right, rules), rules)

    assert result.outcome == MatchOutcome.UNMATCHED


def test_same_id_can_match_by_reference_when_date_is_within_window(rules):
    left = make_transaction("TXN-001", SourceType.BANK)

    right = make_transaction(
        "TXN-001",
        SourceType.LEDGER,
        date=datetime(2026, 11, 21, tzinfo=timezone.utc),
    )

    result = match_exact_pair(make_pair(left, right, rules), rules)

    assert result.outcome == MatchOutcome.CONFIRMED_AUTO
    assert result.rule_id == "REF_01"


def test_reference_match_rejects_amount_mismatch(rules):
    left = make_transaction("BANK-001", SourceType.BANK)

    right = make_transaction(
        "LEDGER-001",
        SourceType.LEDGER,
        amount="99.99",
    )

    result = match_exact_pair(make_pair(left, right, rules), rules)

    assert result.outcome == MatchOutcome.UNMATCHED


def test_result_contains_ruleset_identity(rules):
    left = make_transaction("TXN-001", SourceType.BANK)
    right = make_transaction("TXN-001", SourceType.LEDGER)

    result = match_exact_pair(make_pair(left, right, rules), rules)

    assert result.ruleset_version == rules.version
    assert result.ruleset_hash == rules.fingerprint


def test_result_contains_both_transaction_ids(rules):
    left = make_transaction("BANK-001", SourceType.BANK)
    right = make_transaction("LEDGER-001", SourceType.LEDGER)

    result = match_exact_pair(make_pair(left, right, rules), rules)

    assert result.transaction_ids == ("BANK-001", "LEDGER-001")


def test_result_is_deterministic(rules):
    left = make_transaction("TXN-001", SourceType.BANK)
    right = make_transaction("TXN-001", SourceType.LEDGER)

    pair = make_pair(left, right, rules)

    first = match_exact_pair(pair, rules)
    second = match_exact_pair(pair, rules)

    assert first.model_dump() == second.model_dump()


def test_ruleset_mismatch_is_rejected(rules):
    left = make_transaction("TXN-001", SourceType.BANK)
    right = make_transaction("TXN-001", SourceType.LEDGER)

    pair = MatchingPairInput(
        left=left,
        right=right,
        ruleset_version="2.0.0",
        ruleset_hash=rules.fingerprint,
    )

    with pytest.raises(ValueError, match="ruleset identity"):
        match_exact_pair(pair, rules)


def test_exact_match_records_compared_fields(rules):
    left = make_transaction("TXN-001", SourceType.BANK)
    right = make_transaction("TXN-001", SourceType.LEDGER)

    result = match_exact_pair(make_pair(left, right, rules), rules)

    assert set(result.evidence[0].compared_fields) == {
        "transaction_id",
        "amount",
        "currency",
        "transaction_date",
    }


def test_decimal_amounts_are_compared_exactly(rules):
    left = make_transaction(
        "BANK-001", SourceType.BANK, amount="100.00"
    )

    right = make_transaction(
        "LEDGER-001", SourceType.LEDGER, amount="100.01"
    )

    result = match_exact_pair(make_pair(left, right, rules), rules)

    assert result.outcome == MatchOutcome.UNMATCHED


def test_naive_transaction_datetime_is_rejected(rules):
    left = make_transaction(
        "BANK-001",
        SourceType.BANK,
        date=datetime(2026, 11, 20),
    )

    right = make_transaction("LEDGER-001", SourceType.LEDGER)

    with pytest.raises(ValueError, match="timezone-aware UTC"):
        match_exact_pair(make_pair(left, right, rules), rules)


def test_non_utc_transaction_datetime_is_rejected(rules):
    non_utc = timezone(timedelta(hours=5, minutes=30))

    left = make_transaction(
        "BANK-001",
        SourceType.BANK,
        date=datetime(2026, 11, 20, tzinfo=non_utc),
    )

    right = make_transaction("LEDGER-001", SourceType.LEDGER)

    with pytest.raises(ValueError, match="normalized to UTC"):
        match_exact_pair(make_pair(left, right, rules), rules)

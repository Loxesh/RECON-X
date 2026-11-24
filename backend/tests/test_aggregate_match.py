
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.models.enums import SourceType
from app.reconciliation.aggregate_match import match_aggregate_group
from app.reconciliation.rules import MatchingRuleset
from app.reconciliation.schemas import MatchOutcome, MatchingTransaction


@pytest.fixture
def ruleset():
    return MatchingRuleset()


def transaction(
    transaction_id: str,
    source: SourceType,
    amount: str,
    day: int = 10,
    currency: str = "INR",
) -> MatchingTransaction:
    return MatchingTransaction(
        transaction_id=transaction_id,
        source_type=source,
        transaction_date=datetime(2026, 11, day, tzinfo=timezone.utc),
        amount=Decimal(amount),
        currency=currency,
        fingerprint=f"fingerprint-{transaction_id}",
        reference_norm=f"REF-{transaction_id}",
    )


def test_one_to_many_exact_decimal_total_is_suggested(ruleset):
    bank = transaction("BANK-1", SourceType.BANK, "1000.00")
    ledger_a = transaction("LEDGER-1", SourceType.LEDGER, "400.00")
    ledger_b = transaction("LEDGER-2", SourceType.LEDGER, "600.00")

    result = match_aggregate_group(
        [bank],
        [ledger_a, ledger_b],
        ruleset,
    )

    assert result.outcome == MatchOutcome.SUGGESTED
    assert result.transaction_ids == (
        "BANK-1",
        "LEDGER-1",
        "LEDGER-2",
    )
    assert result.evidence[0].observed_values["grouped_total"] == "1000.00"
    assert result.ruleset_hash == ruleset.fingerprint


def test_many_to_one_exact_decimal_total_is_suggested(ruleset):
    gateway_a = transaction("GATEWAY-1", SourceType.GATEWAY, "250.25")
    gateway_b = transaction("GATEWAY-2", SourceType.GATEWAY, "249.75")
    ledger = transaction("LEDGER-1", SourceType.LEDGER, "500.00")

    result = match_aggregate_group(
        [gateway_a, gateway_b],
        [ledger],
        ruleset,
    )

    assert result.outcome == MatchOutcome.SUGGESTED
    assert set(result.transaction_ids) == {
        "GATEWAY-1",
        "GATEWAY-2",
        "LEDGER-1",
    }


def test_aggregate_never_auto_confirms(ruleset):
    bank = transaction("BANK-1", SourceType.BANK, "100.00")
    ledger_a = transaction("LEDGER-1", SourceType.LEDGER, "40.00")
    ledger_b = transaction("LEDGER-2", SourceType.LEDGER, "60.00")

    result = match_aggregate_group([bank], [ledger_a, ledger_b], ruleset)

    assert result.outcome != MatchOutcome.CONFIRMED_AUTO


def test_amount_mismatch_is_unmatched(ruleset):
    bank = transaction("BANK-1", SourceType.BANK, "1000.00")
    ledger_a = transaction("LEDGER-1", SourceType.LEDGER, "400.00")
    ledger_b = transaction("LEDGER-2", SourceType.LEDGER, "599.99")

    result = match_aggregate_group([bank], [ledger_a, ledger_b], ruleset)

    assert result.outcome == MatchOutcome.UNMATCHED


def test_currency_mismatch_is_unmatched(ruleset):
    bank = transaction("BANK-1", SourceType.BANK, "100.00", currency="INR")
    ledger_a = transaction("LEDGER-1", SourceType.LEDGER, "40.00", currency="INR")
    ledger_b = transaction("LEDGER-2", SourceType.LEDGER, "60.00", currency="USD")

    result = match_aggregate_group([bank], [ledger_a, ledger_b], ruleset)

    assert result.outcome == MatchOutcome.UNMATCHED


def test_date_outside_configured_window_is_unmatched(ruleset):
    bank = transaction("BANK-1", SourceType.BANK, "100.00", day=10)
    ledger_a = transaction("LEDGER-1", SourceType.LEDGER, "40.00", day=10)
    ledger_b = transaction("LEDGER-2", SourceType.LEDGER, "60.00", day=14)

    result = match_aggregate_group([bank], [ledger_a, ledger_b], ruleset)

    assert result.outcome == MatchOutcome.UNMATCHED


def test_group_exceeding_configured_limit_is_rejected(ruleset):
    bank = transaction("BANK-1", SourceType.BANK, "25.00")
    ledger_group = [
        transaction(
            f"LEDGER-{index}",
            SourceType.LEDGER,
            "1.00",
        )
        for index in range(1, 27)
    ]

    with pytest.raises(ValueError, match="maximum group size"):
        match_aggregate_group([bank], ledger_group, ruleset)


def test_non_utc_datetime_is_rejected(ruleset):
    bank = transaction("BANK-1", SourceType.BANK, "100.00")
    ledger_a = transaction("LEDGER-1", SourceType.LEDGER, "40.00")
    ledger_b = transaction("LEDGER-2", SourceType.LEDGER, "60.00")

    invalid_ledger = ledger_b.model_copy(
        update={
            "transaction_date": datetime(
                2026,
                11,
                10,
                tzinfo=timezone(timedelta(hours=5, minutes=30)),
            )
        }
    )

    with pytest.raises(ValueError, match="normalized to UTC"):
        match_aggregate_group([bank], [ledger_a, invalid_ledger], ruleset)

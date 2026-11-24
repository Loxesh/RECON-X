from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.models.enums import SourceType
from app.reconciliation.engine import (
    AggregateCandidateGroup,
    run_reconciliation,
)
from app.reconciliation.rules import MatchingRuleset
from app.reconciliation.schemas import MatchOutcome, MatchingTransaction


@pytest.fixture
def ruleset():
    return MatchingRuleset()


def transaction(
    transaction_id,
    source,
    *,
    reference="REF-100",
    amount="100.00",
    currency="INR",
    description="payment",
    day=20,
):
    return MatchingTransaction(
        transaction_id=transaction_id,
        source_type=source,
        transaction_reference=reference,
        reference_norm=reference,
        transaction_date=datetime(
            2026, 11, day, tzinfo=timezone.utc
        ),
        amount=Decimal(amount),
        currency=currency,
        fingerprint=f"fingerprint-{source.value}-{transaction_id}",
        description_norm=description,
    )


def test_independent_tracks_can_reuse_the_same_ledger_transaction(ruleset):
    bank = transaction("SHARED-1", SourceType.BANK)
    ledger = transaction("SHARED-1", SourceType.LEDGER)
    gateway = transaction("SHARED-1", SourceType.GATEWAY)

    result = run_reconciliation(
        bank_transactions=[bank],
        ledger_transactions=[ledger],
        gateway_transactions=[gateway],
        ruleset=ruleset,
    )

    assert result.bank_ledger.status.confirmed_count == 2
    assert result.gateway_ledger.status.confirmed_count == 2

    assert result.consolidated_status.unique_source_row_count == 3
    assert result.consolidated_status.source_row_counts == {
        "BANK": 1,
        "GATEWAY": 1,
        "LEDGER": 1,
    }


def test_reference_match_is_confirmed_in_bank_track(ruleset):
    bank = transaction(
        "BANK-1", SourceType.BANK, reference="REF-200"
    )
    ledger = transaction(
        "LEDGER-1", SourceType.LEDGER, reference="REF-200"
    )

    result = run_reconciliation(
        bank_transactions=[bank],
        ledger_transactions=[ledger],
        gateway_transactions=[],
        ruleset=ruleset,
    )

    assert result.bank_ledger.matches[0].outcome == MatchOutcome.CONFIRMED_AUTO
    assert result.bank_ledger.status.confirmed_count == 2


def test_fuzzy_candidate_remains_a_suggestion(ruleset):
    bank = transaction(
        "BANK-1",
        SourceType.BANK,
        reference="INV-2026-1001",
        description="monthly subscription payment",
    )
    ledger = transaction(
        "LEDGER-1",
        SourceType.LEDGER,
        reference="INV-2026-100I",
        description="monthly subscription payment",
    )

    result = run_reconciliation(
        bank_transactions=[bank],
        ledger_transactions=[ledger],
        gateway_transactions=[],
        ruleset=ruleset,
    )

    assert result.bank_ledger.matches
    assert all(
        item.outcome != MatchOutcome.CONFIRMED_AUTO
        for item in result.bank_ledger.matches
    )
    assert result.bank_ledger.status.suggested_count + (
        result.bank_ledger.status.ambiguous_count
    ) == 2


def test_explicit_aggregate_group_is_suggested(ruleset):
    bank = transaction(
        "BANK-1", SourceType.BANK, reference="BANK-REF", amount="100.00"
    )
    ledger_a = transaction(
        "LEDGER-1", SourceType.LEDGER, reference="LEDGER-A", amount="40.00"
    )
    ledger_b = transaction(
        "LEDGER-2", SourceType.LEDGER, reference="LEDGER-B", amount="60.00"
    )

    result = run_reconciliation(
        bank_transactions=[bank],
        ledger_transactions=[ledger_a, ledger_b],
        gateway_transactions=[],
        ruleset=ruleset,
        bank_aggregate_candidates=[
            AggregateCandidateGroup(
                left_transaction_ids=("BANK-1",),
                right_transaction_ids=("LEDGER-1", "LEDGER-2"),
            )
        ],
    )

    assert len(result.bank_ledger.aggregate_results) == 1
    assert (
        result.bank_ledger.aggregate_results[0].outcome
        == MatchOutcome.SUGGESTED
    )
    assert result.bank_ledger.status.suggested_count == 3


def test_duplicate_records_are_not_silently_confirmed(ruleset):
    bank_a = transaction("BANK-1", SourceType.BANK)
    bank_b = transaction("BANK-2", SourceType.BANK)
    ledger = transaction("LEDGER-1", SourceType.LEDGER)

    result = run_reconciliation(
        bank_transactions=[bank_a, bank_b],
        ledger_transactions=[ledger],
        gateway_transactions=[],
        ruleset=ruleset,
    )

    assert result.bank_ledger.duplicate_evidence
    assert result.bank_ledger.status.confirmed_count == 0
    assert result.bank_ledger.status.ambiguous_count >= 1


def test_same_reference_amount_mismatch_becomes_exception(ruleset):
    bank = transaction(
        "BANK-1", SourceType.BANK, reference="REF-500", amount="100.00"
    )
    ledger = transaction(
        "LEDGER-1", SourceType.LEDGER, reference="REF-500", amount="105.00"
    )

    result = run_reconciliation(
        bank_transactions=[bank],
        ledger_transactions=[ledger],
        gateway_transactions=[],
        ruleset=ruleset,
    )

    assert result.bank_ledger.exceptions
    assert result.bank_ledger.status.ambiguous_count == 2
    assert result.bank_ledger.status.unmatched_count == 0


def test_unrelated_residual_rows_are_not_compared_as_discrepancies(ruleset):
    bank = transaction(
        "BANK-1", SourceType.BANK, reference="BANK-REF", amount="100.00"
    )
    ledger = transaction(
        "LEDGER-1", SourceType.LEDGER, reference="LEDGER-REF", amount="105.00"
    )

    result = run_reconciliation(
        bank_transactions=[bank],
        ledger_transactions=[ledger],
        gateway_transactions=[],
        ruleset=ruleset,
    )

    assert result.bank_ledger.exceptions == ()
    assert result.bank_ledger.status.unmatched_count == 2


def test_consolidated_totals_count_shared_ledger_once(ruleset):
    bank = transaction(
        "BANK-1", SourceType.BANK, amount="100.00"
    )
    ledger = transaction(
        "LEDGER-1", SourceType.LEDGER, amount="100.00"
    )
    gateway = transaction(
        "GATEWAY-1", SourceType.GATEWAY, amount="100.00"
    )

    result = run_reconciliation(
        bank_transactions=[bank],
        ledger_transactions=[ledger],
        gateway_transactions=[gateway],
        ruleset=ruleset,
    )

    totals = result.consolidated_status.totals_by_source_currency

    assert totals["BANK"]["INR"] == Decimal("100.00")
    assert totals["LEDGER"]["INR"] == Decimal("100.00")
    assert totals["GATEWAY"]["INR"] == Decimal("100.00")
    assert result.consolidated_status.unique_source_row_count == 3


def test_invalid_source_collection_is_rejected(ruleset):
    wrong_source = transaction("LEDGER-1", SourceType.LEDGER)

    with pytest.raises(ValueError, match="unexpected source type"):
        run_reconciliation(
            bank_transactions=[wrong_source],
            ledger_transactions=[],
            gateway_transactions=[],
            ruleset=ruleset,
        )


def test_aggregate_candidate_with_unknown_id_is_rejected(ruleset):
    bank = transaction("BANK-1", SourceType.BANK)
    ledger = transaction("LEDGER-1", SourceType.LEDGER)

    with pytest.raises(ValueError, match="unknown left IDs"):
        run_reconciliation(
            bank_transactions=[bank],
            ledger_transactions=[ledger],
            gateway_transactions=[],
            ruleset=ruleset,
            bank_aggregate_candidates=[
                AggregateCandidateGroup(
                    left_transaction_ids=("UNKNOWN",),
                    right_transaction_ids=("LEDGER-1",),
                )
            ],
        )
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.models.enums import SourceType
from app.reconciliation.discrepancy_detector import (
    DiscrepancyInput,
    DiscrepancyType,
    detect_discrepancies,
)
from app.reconciliation.rules import MatchingRuleset
from app.reconciliation.schemas import MatchingTransaction


def make_transaction(
    transaction_id,
    source,
    amount="100.00",
    currency="INR",
    reference="REF-100",
    date=None,
):
    return MatchingTransaction(
        transaction_id=transaction_id,
        source_type=source,
        transaction_reference=reference,
        reference_norm=reference,
        transaction_date=date or datetime(2026, 11, 20, tzinfo=timezone.utc),
        amount=Decimal(amount),
        currency=currency,
        fingerprint=f"fingerprint-{transaction_id}",
        description_norm="payment",
    )


def compare(left, right, **kwargs):
    return detect_discrepancies(
        DiscrepancyInput(left=left, right=right, **kwargs),
        MatchingRuleset(),
    )


def test_amount_difference_over_configured_tolerance_is_detected():
    left = make_transaction("BANK-1", SourceType.BANK, amount="100.00")
    right = make_transaction("LEDGER-1", SourceType.LEDGER, amount="105.00")

    findings = compare(left, right)

    amount = next(
        item for item in findings
        if item.discrepancy_type == DiscrepancyType.AMOUNT_MISMATCH
    )
    assert amount.difference == Decimal("5.00")
    assert amount.threshold == Decimal("1.00")


def test_amount_difference_within_tolerance_is_not_discrepancy():
    left = make_transaction("BANK-1", SourceType.BANK, amount="100.00")
    right = make_transaction("LEDGER-1", SourceType.LEDGER, amount="100.50")

    findings = compare(left, right)

    assert DiscrepancyType.AMOUNT_MISMATCH not in {
        item.discrepancy_type for item in findings
    }


def test_amount_threshold_can_be_configured():
    left = make_transaction("BANK-1", SourceType.BANK, amount="100.00")
    right = make_transaction("LEDGER-1", SourceType.LEDGER, amount="102.00")
    ruleset = MatchingRuleset(suggested_amount_tolerance=Decimal("2.00"))

    findings = detect_discrepancies(
        DiscrepancyInput(left=left, right=right),
        ruleset,
    )

    assert DiscrepancyType.AMOUNT_MISMATCH not in {
        item.discrepancy_type for item in findings
    }


def test_date_difference_over_bank_ledger_window_is_detected():
    left = make_transaction("BANK-1", SourceType.BANK)
    right = make_transaction(
        "LEDGER-1",
        SourceType.LEDGER,
        date=left.transaction_date + timedelta(days=3),
    )

    findings = compare(left, right)

    date_finding = next(
        item for item in findings
        if item.discrepancy_type == DiscrepancyType.DATE_MISMATCH
    )
    assert date_finding.difference == Decimal("3")
    assert date_finding.threshold == 2


def test_gateway_ledger_uses_its_own_date_window():
    left = make_transaction("GW-1", SourceType.GATEWAY)
    right = make_transaction(
        "LEDGER-1",
        SourceType.LEDGER,
        date=left.transaction_date + timedelta(days=3),
    )

    findings = compare(left, right)

    assert DiscrepancyType.DATE_MISMATCH not in {
        item.discrepancy_type for item in findings
    }


def test_reference_mismatch_is_detected():
    left = make_transaction("BANK-1", SourceType.BANK, reference="REF-100")
    right = make_transaction("LEDGER-1", SourceType.LEDGER, reference="REF-200")

    findings = compare(left, right)

    assert DiscrepancyType.REFERENCE_MISMATCH in {
        item.discrepancy_type for item in findings
    }


def test_reference_comparison_is_normalised():
    left = make_transaction("BANK-1", SourceType.BANK, reference=" ref-100 ")
    right = make_transaction("LEDGER-1", SourceType.LEDGER, reference="REF-100")

    findings = compare(left, right)

    assert DiscrepancyType.REFERENCE_MISMATCH not in {
        item.discrepancy_type for item in findings
    }


def test_currency_mismatch_is_detected_without_amount_comparison():
    left = make_transaction(
        "BANK-1", SourceType.BANK, amount="100.00", currency="INR"
    )
    right = make_transaction(
        "LEDGER-1", SourceType.LEDGER, amount="100.00", currency="USD"
    )

    findings = compare(left, right)
    types = {item.discrepancy_type for item in findings}

    assert DiscrepancyType.CURRENCY_MISMATCH in types
    assert DiscrepancyType.AMOUNT_MISMATCH not in types


def test_status_mismatch_is_detected_when_both_statuses_are_supplied():
    left = make_transaction("BANK-1", SourceType.BANK)
    right = make_transaction("LEDGER-1", SourceType.LEDGER)

    findings = compare(
        left,
        right,
        left_status="SETTLED",
        right_status="PENDING",
    )

    assert DiscrepancyType.STATUS_MISMATCH in {
        item.discrepancy_type for item in findings
    }


def test_equal_statuses_do_not_create_status_discrepancy():
    left = make_transaction("BANK-1", SourceType.BANK)
    right = make_transaction("LEDGER-1", SourceType.LEDGER)

    findings = compare(
        left,
        right,
        left_status="settled",
        right_status="SETTLED",
    )

    assert DiscrepancyType.STATUS_MISMATCH not in {
        item.discrepancy_type for item in findings
    }


def test_status_must_be_supplied_for_both_sides():
    left = make_transaction("BANK-1", SourceType.BANK)
    right = make_transaction("LEDGER-1", SourceType.LEDGER)

    with pytest.raises(ValueError, match="Both statuses"):
        DiscrepancyInput(
            left=left,
            right=right,
            left_status="SETTLED",
        )


def test_unsupported_source_pair_is_rejected():
    bank = make_transaction("BANK-1", SourceType.BANK)
    gateway = make_transaction("GW-1", SourceType.GATEWAY)

    with pytest.raises(ValueError, match="Unsupported source combination"):
        DiscrepancyInput(left=bank, right=gateway)


def test_same_internal_transaction_id_is_rejected():
    left = make_transaction("TXN-1", SourceType.BANK)
    right = make_transaction("TXN-1", SourceType.LEDGER)

    with pytest.raises(ValueError, match="different internal IDs"):
        compare(left, right)


def test_matching_pair_with_no_discrepancy_returns_empty_tuple():
    left = make_transaction("BANK-1", SourceType.BANK)
    right = make_transaction("LEDGER-1", SourceType.LEDGER)

    assert compare(left, right) == ()
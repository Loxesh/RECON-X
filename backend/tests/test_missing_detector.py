
from datetime import datetime, timezone
from decimal import Decimal

from app.models.enums import SourceType
from app.reconciliation.missing_detector import (
    MissingClassification,
    detect_missing_transactions,
)
from app.reconciliation.schemas import MatchingTransaction


def make_transaction(transaction_id, source):
    return MatchingTransaction(
        transaction_id=transaction_id,
        source_type=source,
        transaction_reference=f"REF-{transaction_id}",
        reference_norm=f"REF-{transaction_id}",
        transaction_date=datetime(2026, 11, 20, tzinfo=timezone.utc),
        amount=Decimal("100.00"),
        currency="INR",
        fingerprint=f"fingerprint-{transaction_id}",
        description_norm="payment",
    )


def test_bank_transaction_missing_from_ledger():
    bank = make_transaction("BANK-001", SourceType.BANK)

    findings = detect_missing_transactions(
        [bank],
        [],
        expected_left_source=SourceType.BANK,
        expected_right_source=SourceType.LEDGER,
    )

    assert len(findings) == 1
    assert findings[0].classification == (
        MissingClassification.MISSING_FROM_LEDGER
    )
    assert findings[0].transaction_id == "BANK-001"


def test_ledger_transaction_missing_from_bank():
    ledger = make_transaction("LEDGER-001", SourceType.LEDGER)

    findings = detect_missing_transactions(
        [],
        [ledger],
        expected_left_source=SourceType.BANK,
        expected_right_source=SourceType.LEDGER,
    )

    assert len(findings) == 1
    assert findings[0].classification == (
        MissingClassification.MISSING_FROM_BANK
    )


def test_gateway_transaction_missing_from_ledger():
    gateway = make_transaction("GW-001", SourceType.GATEWAY)

    findings = detect_missing_transactions(
        [gateway],
        [],
        expected_left_source=SourceType.GATEWAY,
        expected_right_source=SourceType.LEDGER,
    )

    assert findings[0].classification == (
        MissingClassification.MISSING_FROM_LEDGER
    )


def test_both_sides_empty_returns_no_findings():
    assert detect_missing_transactions(
        [],
        [],
        expected_left_source=SourceType.BANK,
        expected_right_source=SourceType.LEDGER,
    ) == ()


def test_both_sides_unmatched_are_classified():
    bank = make_transaction("BANK-001", SourceType.BANK)
    ledger = make_transaction("LEDGER-001", SourceType.LEDGER)

    findings = detect_missing_transactions(
        [bank],
        [ledger],
        expected_left_source=SourceType.BANK,
        expected_right_source=SourceType.LEDGER,
    )

    assert len(findings) == 2
    assert {
        item.classification for item in findings
    } == {
        MissingClassification.MISSING_FROM_BANK,
        MissingClassification.MISSING_FROM_LEDGER,
    }


def test_unsupported_source_pair_is_rejected():
    bank = make_transaction("BANK-001", SourceType.BANK)
    gateway = make_transaction("GW-001", SourceType.GATEWAY)

    import pytest

    with pytest.raises(ValueError, match="Unsupported source combination"):
        detect_missing_transactions(
            [bank],
            [gateway],
            expected_left_source=SourceType.BANK,
            expected_right_source=SourceType.GATEWAY,
        )


def test_wrong_source_on_left_side_is_rejected():
    ledger = make_transaction("LEDGER-001", SourceType.LEDGER)

    import pytest

    with pytest.raises(ValueError, match="expected_left_source"):
        detect_missing_transactions(
            [ledger],
            [],
            expected_left_source=SourceType.BANK,
            expected_right_source=SourceType.LEDGER,
        )

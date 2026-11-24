
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.models.enums import SourceType
from app.reconciliation.duplicate_detector import (
    DuplicateClassification,
    create_duplicate_fingerprint,
    detect_duplicates,
)
from app.reconciliation.schemas import MatchingTransaction


def make_transaction(
    transaction_id,
    reference="REF-100",
    amount="100.00",
    date=None,
    description="payment",
    source=SourceType.BANK,
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
        currency="INR",
        fingerprint=f"source-row-{transaction_id}",
        description_norm=description,
    )


def test_same_canonical_transaction_is_duplicate():
    first = make_transaction("ROW-1")
    second = make_transaction("ROW-2")

    findings = detect_duplicates([first, second])

    assert len(findings) == 1
    assert findings[0].classification == DuplicateClassification.DUPLICATE
    assert findings[0].transaction_ids == ("ROW-1", "ROW-2")


def test_same_amount_and_date_with_different_references_is_not_duplicate():
    first = make_transaction("ROW-1", reference="PAY-001")
    second = make_transaction("ROW-2", reference="PAY-002")

    assert detect_duplicates([first, second]) == ()


def test_same_reference_with_different_amount_is_conflict_not_duplicate():
    first = make_transaction("ROW-1", amount="100.00")
    second = make_transaction("ROW-2", amount="150.00")

    findings = detect_duplicates([first, second])

    assert len(findings) == 1
    assert findings[0].classification == (
        DuplicateClassification.REFERENCE_CONFLICT
    )


def test_fingerprint_is_stable():
    first = make_transaction("ROW-1")
    second = make_transaction("ROW-2")

    assert create_duplicate_fingerprint(first) == (
        create_duplicate_fingerprint(second)
    )


def test_fingerprint_changes_when_reference_changes():
    first = make_transaction("ROW-1", reference="PAY-001")
    second = make_transaction("ROW-2", reference="PAY-002")

    assert create_duplicate_fingerprint(first) != (
        create_duplicate_fingerprint(second)
    )


def test_missing_reference_cannot_create_fingerprint():
    transaction = make_transaction("ROW-1", reference=None)

    with pytest.raises(ValueError, match="stable transaction reference"):
        create_duplicate_fingerprint(transaction)


def test_duplicate_detection_rejects_duplicate_internal_ids():
    first = make_transaction("ROW-1")
    second = make_transaction("ROW-1")

    with pytest.raises(ValueError, match="unique internal transaction IDs"):
        detect_duplicates([first, second])


def test_fingerprint_is_source_specific():
    bank = make_transaction("ROW-1", source=SourceType.BANK)
    ledger = make_transaction("ROW-2", source=SourceType.LEDGER)

    assert create_duplicate_fingerprint(bank) != (
        create_duplicate_fingerprint(ledger)
    )

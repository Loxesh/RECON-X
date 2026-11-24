from datetime import datetime, timezone
from decimal import Decimal

from app.models.enums import RiskLevel, SourceType
from app.reconciliation.discrepancy_detector import (
    DiscrepancyEvidence,
    DiscrepancyType,
)
from app.reconciliation.exception_classifier import (
    ClassifiedException,
    ExceptionLifecycle,
    SuggestedAction,
    classify_discrepancies,
)


def make_finding(
    discrepancy_type,
    transaction_ids=("BANK-1", "LEDGER-1"),
):
    return DiscrepancyEvidence(
        discrepancy_type=discrepancy_type,
        transaction_ids=transaction_ids,
        source_types=(SourceType.BANK.value, SourceType.LEDGER.value),
        reason=f"Detected {discrepancy_type.value.lower()}.",
        compared_fields=("test_field",),
        observed_values={"left": "A", "right": "B"},
        difference=Decimal("5.00")
        if discrepancy_type == DiscrepancyType.AMOUNT_MISMATCH
        else None,
    )


def test_amount_mismatch_creates_medium_open_exception():
    result = classify_discrepancies(
        [make_finding(DiscrepancyType.AMOUNT_MISMATCH)]
    )

    assert len(result) == 1
    exception = result[0]
    assert isinstance(exception, ClassifiedException)
    assert exception.exception_type == DiscrepancyType.AMOUNT_MISMATCH
    assert exception.severity == RiskLevel.MEDIUM
    assert exception.lifecycle_state == ExceptionLifecycle.OPEN
    assert exception.review_required is True
    assert exception.suggested_action == SuggestedAction.REVIEW_AMOUNT


def test_currency_mismatch_uses_conservative_high_severity():
    result = classify_discrepancies(
        [make_finding(DiscrepancyType.CURRENCY_MISMATCH)]
    )

    assert result[0].severity == RiskLevel.HIGH
    assert result[0].suggested_action == SuggestedAction.VERIFY_CURRENCY


def test_status_mismatch_is_review_required():
    result = classify_discrepancies(
        [make_finding(DiscrepancyType.STATUS_MISMATCH)]
    )

    assert result[0].severity == RiskLevel.HIGH
    assert result[0].review_required is True
    assert result[0].suggested_action == SuggestedAction.VERIFY_SOURCE_STATUS


def test_multiple_findings_for_pair_create_one_primary_exception():
    findings = [
        make_finding(DiscrepancyType.AMOUNT_MISMATCH),
        make_finding(DiscrepancyType.DATE_MISMATCH),
        make_finding(DiscrepancyType.CURRENCY_MISMATCH),
    ]

    result = classify_discrepancies(findings)

    assert len(result) == 1
    assert result[0].exception_type == DiscrepancyType.CURRENCY_MISMATCH
    assert len(result[0].evidence) == 3
    assert set(result[0].primary_txn_ids) == {"BANK-1", "LEDGER-1"}


def test_distinct_transaction_pairs_create_distinct_exceptions():
    findings = [
        make_finding(
            DiscrepancyType.AMOUNT_MISMATCH,
            ("BANK-1", "LEDGER-1"),
        ),
        make_finding(
            DiscrepancyType.DATE_MISMATCH,
            ("BANK-2", "LEDGER-2"),
        ),
    ]

    result = classify_discrepancies(findings)

    assert len(result) == 2


def test_severity_policy_can_be_overridden():
    result = classify_discrepancies(
        [make_finding(DiscrepancyType.AMOUNT_MISMATCH)],
        severity_policy={
            DiscrepancyType.AMOUNT_MISMATCH: RiskLevel.HIGH,
        },
    )

    assert result[0].severity == RiskLevel.HIGH


def test_empty_findings_return_empty_tuple():
    assert classify_discrepancies([]) == ()


def test_classification_does_not_auto_approve_exception():
    result = classify_discrepancies(
        [make_finding(DiscrepancyType.AMOUNT_MISMATCH)]
    )

    assert result[0].lifecycle_state == ExceptionLifecycle.OPEN
    assert result[0].review_required is True
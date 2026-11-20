
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.ingestion.normalizer import (
    normalize_amount,
    normalize_currency,
    normalize_date,
    normalize_direction,
    normalize_reference,
    normalize_row,
)
from app.models.enums import TransactionDirection


def make_row(canonical_row, raw_row=None, issues=None):
    return SimpleNamespace(
        source_row_number=2,
        sheet_name="Sheet1",
        raw_row=raw_row or dict(canonical_row),
        canonical_row=canonical_row,
        issues=issues or [],
        is_valid=not bool(issues),
    )


def test_normalize_iso_date_with_explicit_timezone():
    result = normalize_date("2026-11-20 10:30:00", "Asia/Kolkata")

    assert result == datetime(2026, 11, 20, 5, 0, tzinfo=timezone.utc)
    assert result.tzinfo == timezone.utc


def test_normalize_date_with_existing_timezone():
    result = normalize_date("2026-11-20T10:30:00+05:30")

    assert result == datetime(2026, 11, 20, 5, 0, tzinfo=timezone.utc)


def test_normalize_date_only_with_explicit_timezone():
    result = normalize_date("20/11/2026", "Asia/Kolkata")

    assert result == datetime(2026, 11, 19, 18, 30, tzinfo=timezone.utc)


def test_naive_date_requires_timezone():
    with pytest.raises(ValueError, match="timezone"):
        normalize_date("2026-11-20 10:30:00")


def test_invalid_date_is_rejected():
    with pytest.raises(ValueError, match="Unsupported"):
        normalize_date("not-a-date", "UTC")


def test_unknown_timezone_is_rejected():
    with pytest.raises(ValueError, match="Unknown source timezone"):
        normalize_date("2026-11-20", "Invalid/Timezone")


@pytest.mark.parametrize(
    ("value", "expected_amount", "expected_direction"),
    [
        ("15000.00", Decimal("15000.00"), TransactionDirection.CREDIT),
        ("-5000.00", Decimal("5000.00"), TransactionDirection.DEBIT),
        ("1,234.56", Decimal("1234.56"), TransactionDirection.CREDIT),
        (Decimal("-250.00"), Decimal("250.00"), TransactionDirection.DEBIT),
        (0, Decimal("0"), TransactionDirection.CREDIT),
    ],
)
def test_normalize_amount(value, expected_amount, expected_direction):
    amount, direction = normalize_amount(value)

    assert amount == expected_amount
    assert isinstance(amount, Decimal)
    assert direction == expected_direction


@pytest.mark.parametrize("value", [True, 12.5, float("nan"), float("inf")])
def test_normalize_amount_rejects_float_and_boolean(value):
    with pytest.raises(ValueError):
        normalize_amount(value)


@pytest.mark.parametrize("value", ["", "12,34.50", "abc", "NaN", "Infinity"])
def test_normalize_amount_rejects_invalid_values(value):
    with pytest.raises(ValueError):
        normalize_amount(value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("credit", TransactionDirection.CREDIT),
        ("CR", TransactionDirection.CREDIT),
        ("debit", TransactionDirection.DEBIT),
        ("DR", TransactionDirection.DEBIT),
    ],
)
def test_normalize_direction(value, expected):
    assert normalize_direction(value) == expected


def test_invalid_direction_is_rejected():
    with pytest.raises(ValueError, match="Unsupported"):
        normalize_direction("TRANSFER")


@pytest.mark.parametrize(
    ("value", "expected"),
    [(" inr ", "INR"), ("usd", "USD"), ("eur", "EUR")],
)
def test_normalize_currency(value, expected):
    assert normalize_currency(value) == expected


@pytest.mark.parametrize("value", ["IN", "USDD", "12R", "", None])
def test_invalid_currency_is_rejected(value):
    with pytest.raises(ValueError):
        normalize_currency(value)


def test_normalize_reference():
    assert normalize_reference("  utr-123abc  ") == "UTR-123ABC"
    assert normalize_reference("   ") is None
    assert normalize_reference(None) is None


def test_normalize_valid_row_preserves_raw_data():
    raw = {
        "transaction_date": "2026-11-20",
        "amount": "-5000.00",
        "currency": "inr",
        "reference": " utr-001 ",
        "description": "  ATM   withdrawal ",
    }
    canonical = {
        "txn_date": raw["transaction_date"],
        "amount": raw["amount"],
        "currency": raw["currency"],
        "reference_norm": raw["reference"],
        "description": raw["description"],
    }

    row = make_row(canonical, raw)
    result = normalize_row(row, "Asia/Kolkata")

    assert result.is_valid
    assert result.raw_row == raw
    assert result.canonical_row["amount"] == Decimal("5000.00")
    assert result.canonical_row["direction"] == TransactionDirection.DEBIT
    assert result.canonical_row["currency"] == "INR"
    assert result.canonical_row["reference_norm"] == "UTR-001"
    assert result.canonical_row["description_norm"] == "atm withdrawal"


def test_explicit_direction_must_match_amount_sign():
    row = make_row({
        "txn_date": "2026-11-20T10:00:00Z",
        "amount": "-500",
        "currency": "INR",
        "direction": "CREDIT",
    })

    result = normalize_row(row)

    assert not result.is_valid
    assert any(issue.code == "INVALID_DIRECTION" for issue in result.issues)


def test_missing_currency_is_reported():
    row = make_row({
        "txn_date": "2026-11-20T10:00:00Z",
        "amount": "500",
    })

    result = normalize_row(row)

    assert any(issue.code == "MISSING_CURRENCY" for issue in result.issues)


def test_invalid_values_are_reported_without_dropping_raw_row():
    raw = {"date": "bad-date", "amount": "not-money", "currency": "IN"}
    row = make_row(
        {
            "txn_date": raw["date"],
            "amount": raw["amount"],
            "currency": raw["currency"],
        },
        raw,
    )

    result = normalize_row(row, "UTC")

    assert not result.is_valid
    assert result.raw_row == raw
    assert {issue.field for issue in result.issues} == {
        "txn_date",
        "amount",
        "currency",
        "direction",
    }


def test_upstream_invalid_row_is_not_normalized():
    row = make_row(
        {"txn_date": "2026-11-20", "amount": "500", "currency": "INR"},
        issues=["missing field"],
    )

    result = normalize_row(row, "UTC")

    assert not result.is_valid
    assert result.canonical_row == {}
    assert result.issues[0].code == "UPSTREAM_VALIDATION_FAILED"

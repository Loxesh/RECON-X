
from datetime import datetime
from decimal import Decimal

import pytest

from app.ingestion.provenance import (
    RowProvenance,
    create_provenance,
    create_transaction_fingerprint,
)
from app.models.enums import SourceType


def test_create_provenance():
    raw = {
        "transaction_date": "2026-11-20",
        "amount": "-500.00",
        "reference": "UTR001",
    }

    provenance = create_provenance(
        filename="bank_statement.csv",
        source_type=SourceType.BANK,
        source_row_number=4,
        raw_row=raw,
    )

    assert provenance.source_filename == "bank_statement.csv"
    assert provenance.source_type == SourceType.BANK
    assert provenance.source_row_number == 4
    assert provenance.sheet_name is None
    assert provenance.raw_row == raw
    assert len(provenance.raw_sha256) == 64


def test_xlsx_provenance_preserves_sheet_name():
    provenance = create_provenance(
        filename="bank_statement.xlsx",
        source_type="BANK",
        source_row_number=8,
        raw_row={"amount": Decimal("500.25")},
        sheet_name="November",
    )

    assert provenance.sheet_name == "November"


def test_raw_hash_is_deterministic():
    first = create_provenance(
        "statement.csv", "BANK", 2, {"amount": "100", "reference": "A1"}
    )
    second = create_provenance(
        "statement.csv", "BANK", 2, {"reference": "A1", "amount": "100"}
    )

    assert first.raw_sha256 == second.raw_sha256


def test_raw_hash_changes_when_source_data_changes():
    first = create_provenance(
        "statement.csv", "BANK", 2, {"amount": "100"}
    )
    second = create_provenance(
        "statement.csv", "BANK", 2, {"amount": "200"}
    )

    assert first.raw_sha256 != second.raw_sha256


@pytest.mark.parametrize(
    ("filename", "source_type", "row_number", "raw_row"),
    [
        ("", "BANK", 1, {}),
        ("statement.csv", "INVALID", 1, {}),
        ("statement.csv", "BANK", 0, {}),
        ("statement.csv", "BANK", -1, {}),
        ("statement.csv", "BANK", 1, []),
    ],
)
def test_invalid_provenance_inputs_are_rejected(
    filename, source_type, row_number, raw_row
):
    with pytest.raises(ValueError):
        create_provenance(filename, source_type, row_number, raw_row)


def test_transaction_fingerprint_is_deterministic():
    provenance = create_provenance(
        "statement.csv",
        "BANK",
        2,
        {"amount": "-100.00", "reference": "A1"},
    )
    canonical = {
        "amount": Decimal("100.00"),
        "currency": "INR",
        "direction": "DEBIT",
        "txn_date": datetime.fromisoformat("2026-11-20T00:00:00+00:00"),
    }

    first = create_transaction_fingerprint(provenance, canonical)
    second = create_transaction_fingerprint(provenance, canonical)

    assert first == second
    assert len(first) == 64


def test_transaction_fingerprint_changes_when_canonical_data_changes():
    provenance = create_provenance(
        "statement.csv", "BANK", 2, {"amount": "-100.00"}
    )

    first = create_transaction_fingerprint(
        provenance, {"amount": Decimal("100.00")}
    )
    second = create_transaction_fingerprint(
        provenance, {"amount": Decimal("200.00")}
    )

    assert first != second


def test_fingerprint_requires_valid_inputs():
    with pytest.raises(TypeError):
        create_transaction_fingerprint(
            "not provenance", {"amount": Decimal("100")}
        )

    provenance = create_provenance(
        "statement.csv", "BANK", 2, {"amount": "100"}
    )

    with pytest.raises(ValueError):
        create_transaction_fingerprint(provenance, [])


import pytest

from app.ingestion.csv_xlsx_parser import ParsedRow
from app.ingestion.header_mapper import (
    HeaderMappingError,
    map_headers,
)
from app.ingestion.validators import validate_parsed_rows
from app.models.enums import SourceType


@pytest.mark.parametrize(
    ("source", "headers"),
    [
        (
            SourceType.BANK,
            ["transaction_id", "transaction_date", "description",
             "amount", "reference"],
        ),
        (
            SourceType.LEDGER,
            ["journal_id", "posting_date", "narration",
             "transaction_amount", "journal_reference"],
        ),
        (
            SourceType.GATEWAY,
            ["payment_intent_id", "payment_date", "details",
             "net_amount", "settlement_id"],
        ),
    ],
)
def test_maps_supported_source_headers(source, headers):
    result = map_headers(headers, source)

    assert result.is_valid
    assert result.field_map["txn_date"] == headers[1]
    assert result.field_map["amount"] == headers[3]


def test_sample_bank_statement_headers_are_supported():
    result = map_headers(
        [
            "transaction_id",
            "transaction_date",
            "description",
            "amount",
            "reference",
        ],
        SourceType.BANK,
    )

    assert result.is_valid
    assert result.field_map["txn_ref"] == "transaction_id"
    assert result.field_map["reference_norm"] == "reference"


def test_missing_amount_header_is_reported():
    result = map_headers(
        ["transaction_id", "transaction_date"],
        SourceType.BANK,
    )

    assert not result.is_valid
    assert any(
        issue.code == "MISSING_REQUIRED_HEADER"
        and issue.header == "amount"
        for issue in result.issues
    )


def test_unknown_header_is_reported():
    result = map_headers(
        ["transaction_date", "amount", "mystery_column"],
        SourceType.BANK,
    )

    assert "mystery_column" in result.unknown_headers
    assert any(issue.code == "UNKNOWN_HEADER" for issue in result.issues)


def test_duplicate_canonical_mapping_is_ambiguous():
    result = map_headers(
        ["date", "transaction_date", "amount"],
        SourceType.BANK,
    )

    assert not result.is_valid
    assert any(
        issue.code == "AMBIGUOUS_HEADER"
        for issue in result.issues
    )


def test_empty_header_is_reported():
    result = map_headers(
        ["transaction_date", "amount", ""],
        SourceType.BANK,
    )

    assert not result.is_valid
    assert any(issue.code == "EMPTY_HEADER" for issue in result.issues)


def test_invalid_source_type_raises_error():
    with pytest.raises(HeaderMappingError):
        map_headers(["date", "amount"], "UNKNOWN")


def test_row_validation_preserves_valid_and_invalid_rows():
    mapping = map_headers(
        ["transaction_date", "amount", "description"],
        SourceType.BANK,
    )

    rows = [
        ParsedRow(
            source_row_number=2,
            raw_row={
                "transaction_date": "2026-11-15",
                "amount": "15000.00",
                "description": "Customer Payment",
            },
        ),
        ParsedRow(
            source_row_number=3,
            raw_row={
                "transaction_date": "2026-11-16",
                "amount": "",
                "description": "Vendor Payment",
            },
        ),
    ]

    result = validate_parsed_rows(rows, mapping)

    assert len(result.rows) == 2
    assert result.valid_count == 1
    assert result.invalid_count == 1
    assert result.rows[0].source_row_number == 2
    assert result.rows[1].source_row_number == 3
    assert result.rows[1].issues[0].field == "amount"
    assert result.rows[1].raw_row["amount"] == ""


def test_mapping_issues_prevent_row_validation():
    mapping = map_headers(
        ["transaction_date"],
        SourceType.BANK,
    )

    result = validate_parsed_rows(
        [
            ParsedRow(
                source_row_number=2,
                raw_row={"transaction_date": "2026-11-15"},
            )
        ],
        mapping,
    )

    assert result.rows == []
    assert result.mapping_issues

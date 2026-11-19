from io import BytesIO

import pytest
from openpyxl import Workbook

from app.ingestion.csv_xlsx_parser import (
    ParserError,
    parse_uploaded_file,
)


def make_xlsx() -> bytes:
    """Create a synthetic workbook containing two worksheets."""

    workbook = Workbook()

    bank = workbook.active
    bank.title = "Bank"
    bank.append(["transaction_id", "amount"])
    bank.append(["TXN001", 15000.00])
    bank.append(["TXN002", -5000.00])

    ledger = workbook.create_sheet("Ledger")
    ledger.append(["entry_id", "amount"])
    ledger.append(["LED001", 15000.00])

    buffer = BytesIO()
    workbook.save(buffer)
    workbook.close()

    return buffer.getvalue()


def test_parse_valid_csv_preserves_values_and_source_rows():
    content = (
        b"transaction_id,amount\n"
        b"TXN001,15000.00\n"
        b"TXN002,-5000.00\n"
    )

    result = parse_uploaded_file("bank.csv", content)

    assert len(result.rows) == 2
    assert result.issues == []
    assert result.rows[0].source_row_number == 2
    assert result.rows[0].raw_row == {
        "transaction_id": "TXN001",
        "amount": "15000.00",
    }
    assert result.rows[1].source_row_number == 3
    assert result.encoding == "utf-8-sig"


def test_parse_csv_with_utf8_bom():
    content = (
        "\ufefftransaction_id,description\n"
        "TXN001,Payment\n"
    ).encode("utf-8")

    result = parse_uploaded_file("bank.csv", content)

    assert result.rows[0].raw_row["transaction_id"] == "TXN001"
    assert result.encoding == "utf-8-sig"


def test_parse_csv_with_windows_1252_encoding():
    content = (
        "transaction_id,description\n"
        "TXN001,Café payment\n"
    ).encode("cp1252")

    result = parse_uploaded_file("bank.csv", content)

    assert result.encoding == "cp1252"
    assert result.rows[0].raw_row["description"] == "Café payment"


def test_malformed_csv_row_is_reported():
    content = (
        b"transaction_id,amount\n"
        b"TXN001,15000.00\n"
        b"TXN002\n"
    )

    result = parse_uploaded_file("bank.csv", content)

    assert len(result.rows) == 1
    assert len(result.issues) == 1
    assert result.issues[0].source_row_number == 3
    assert "expected 2" in result.issues[0].message


def test_empty_csv_is_reported():
    result = parse_uploaded_file("empty.csv", b"")

    assert result.rows == []
    assert len(result.issues) == 1
    assert "empty" in result.issues[0].message.lower()


def test_csv_without_header_is_reported():
    result = parse_uploaded_file("empty.csv", b"")

    assert result.rows == []
    assert result.issues


def test_duplicate_csv_headers_are_reported():
    content = b"transaction_id,amount,amount\nTXN001,100,200\n"

    result = parse_uploaded_file("bank.csv", content)

    assert result.rows == []
    assert "duplicate" in result.issues[0].message.lower()


def test_parse_xlsx_preserves_multiple_sheets_and_rows():
    result = parse_uploaded_file("statements.xlsx", make_xlsx())

    assert result.sheets == ["Bank", "Ledger"]
    assert len(result.rows) == 3
    assert result.issues == []

    assert result.rows[0].sheet_name == "Bank"
    assert result.rows[0].source_row_number == 2
    assert result.rows[0].raw_row["transaction_id"] == "TXN001"
    assert result.rows[0].raw_row["amount"] == 15000.00

    assert result.rows[2].sheet_name == "Ledger"
    assert result.rows[2].source_row_number == 2


def test_xlsx_malformed_row_is_reported():
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["transaction_id", "amount"])
    sheet.append(["TXN001", 100])
    sheet.append(["TXN002", 200, "unexpected"])

    buffer = BytesIO()
    workbook.save(buffer)
    workbook.close()

    result = parse_uploaded_file("bank.xlsx", buffer.getvalue())

    assert len(result.rows) == 1
    assert len(result.issues) == 1
    assert result.issues[0].sheet_name == "Sheet"
    assert result.issues[0].source_row_number == 3


def test_macro_enabled_excel_extension_is_rejected():
    with pytest.raises(ParserError, match="Macro-enabled"):
        parse_uploaded_file("bank.xlsm", b"test")


def test_unsupported_file_extension_is_rejected():
    with pytest.raises(ParserError, match="Only CSV and XLSX"):
        parse_uploaded_file("bank.pdf", b"test")


def test_corrupt_xlsx_is_rejected():
    with pytest.raises(ParserError, match="XLSX"):
        parse_uploaded_file("bank.xlsx", b"not an Excel workbook")


def test_invalid_filename_is_rejected():
    with pytest.raises(ParserError, match="Invalid filename"):
        parse_uploaded_file("../bank.csv", b"id,amount\n1,100\n")
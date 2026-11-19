
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from app.ingestion.file_validator import (
    FileValidationError,
    validate_uploaded_file,
)


def valid_csv():
    return b"date,amount,reference\n2026-01-01,100,TXN001\n"


def valid_xlsx():
    buffer = BytesIO()

    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0"?><Types></Types>',
        )
        archive.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0"?><workbook></workbook>',
        )

    return buffer.getvalue()


def test_valid_csv_is_accepted():
    content = valid_csv()

    result = validate_uploaded_file(
        filename="transactions.csv",
        content_type="text/csv",
        content=content,
        max_size_bytes=1024,
    )

    assert result.original_filename == "transactions.csv"
    assert result.extension == ".csv"
    assert result.size_bytes == len(content)


def test_valid_xlsx_is_accepted():
    content = valid_xlsx()

    result = validate_uploaded_file(
        filename="transactions.xlsx",
        content_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        content=content,
        max_size_bytes=1024 * 10,
    )

    assert result.extension == ".xlsx"
    assert result.content == content


def test_unsupported_extension_is_rejected():
    with pytest.raises(FileValidationError):
        validate_uploaded_file(
            "transactions.exe",
            "application/octet-stream",
            b"content",
            1024,
        )


def test_empty_file_is_rejected():
    with pytest.raises(FileValidationError):
        validate_uploaded_file(
            "transactions.csv",
            "text/csv",
            b"",
            1024,
        )


def test_oversized_file_is_rejected():
    with pytest.raises(FileValidationError):
        validate_uploaded_file(
            "transactions.csv",
            "text/csv",
            valid_csv(),
            5,
        )


def test_mismatched_mime_type_is_rejected():
    with pytest.raises(FileValidationError):
        validate_uploaded_file(
            "transactions.csv",
            "application/pdf",
            valid_csv(),
            1024,
        )


def test_path_traversal_filename_is_rejected():
    with pytest.raises(FileValidationError):
        validate_uploaded_file(
            "../transactions.csv",
            "text/csv",
            valid_csv(),
            1024,
        )


def test_invalid_csv_encoding_is_rejected():
    with pytest.raises(FileValidationError):
        validate_uploaded_file(
            "transactions.csv",
            "text/csv",
            b"\xff\xfe\x00\x00",
            1024,
        )


def test_csv_without_header_is_rejected():
    with pytest.raises(FileValidationError):
        validate_uploaded_file(
            "transactions.csv",
            "text/csv",
            b"\n",
            1024,
        )


def test_corrupt_xlsx_is_rejected():
    with pytest.raises(FileValidationError):
        validate_uploaded_file(
            "transactions.xlsx",
            (
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            b"not-a-real-xlsx-file",
            1024,
        )

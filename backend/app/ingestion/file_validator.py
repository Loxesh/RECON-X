
"""Secure validation for uploaded financial files."""

from dataclasses import dataclass
from pathlib import PurePath
from zipfile import BadZipFile, ZipFile
from io import BytesIO
import csv
import io


ALLOWED_EXTENSIONS = {".csv", ".xlsx"}

ALLOWED_MIME_TYPES = {
    ".csv": {
        "text/csv",
        "application/csv",
        "application/vnd.ms-excel",
        "text/plain",
    },
    ".xlsx": {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    },
}


@dataclass(frozen=True)
class ValidatedFile:
    original_filename: str
    extension: str
    content_type: str
    size_bytes: int
    content: bytes


class FileValidationError(ValueError):
    """Raised when an uploaded file violates security rules."""


def validate_uploaded_file(
    filename: str | None,
    content_type: str | None,
    content: bytes,
    max_size_bytes: int,
) -> ValidatedFile:
    """Validate filename, extension, MIME type, size and basic content."""

    if not filename or not filename.strip():
        raise FileValidationError("A filename is required.")

    safe_name = PurePath(filename.replace("\\", "/")).name

    if safe_name != filename or safe_name in {".", ".."}:
        raise FileValidationError("Invalid filename.")

    if len(safe_name) > 255:
        raise FileValidationError("Filename is too long.")

    extension = PurePath(safe_name).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise FileValidationError("Only CSV and XLSX files are allowed.")

    if not content:
        raise FileValidationError("The uploaded file is empty.")

    if len(content) > max_size_bytes:
        raise FileValidationError("Uploaded file exceeds the size limit.")

    normalized_mime = (content_type or "").split(";")[0].strip().lower()

    if normalized_mime not in ALLOWED_MIME_TYPES[extension]:
        raise FileValidationError(
            "File extension and MIME type do not match an allowed format."
        )

    if extension == ".csv":
        _validate_csv_content(content)

    if extension == ".xlsx":
        _validate_xlsx_content(content)

    return ValidatedFile(
        original_filename=safe_name,
        extension=extension,
        content_type=normalized_mime,
        size_bytes=len(content),
        content=content,
    )


def _validate_csv_content(content: bytes) -> None:
    """Reject binary or unreadable CSV content."""

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise FileValidationError(
            "CSV must use UTF-8 encoding."
        ) from None

    if "\x00" in text:
        raise FileValidationError("CSV contains invalid binary data.")

    try:
        rows = csv.reader(io.StringIO(text))
        first_row = next(rows, None)
    except csv.Error:
        raise FileValidationError("CSV content is malformed.") from None

    if not first_row or not any(cell.strip() for cell in first_row):
        raise FileValidationError("CSV does not contain a valid header row.")


def _validate_xlsx_content(content: bytes) -> None:
    """Check that the file is a valid XLSX ZIP container."""

    try:
        with ZipFile(BytesIO(content)) as archive:
            names = set(archive.namelist())

            if (
                "[Content_Types].xml" not in names
                or "xl/workbook.xml" not in names
            ):
                raise FileValidationError(
                    "The uploaded XLSX file is not a valid workbook."
                )

            if archive.testzip() is not None:
                raise FileValidationError(
                    "The XLSX file contains a corrupted archive entry."
                )

    except BadZipFile:
        raise FileValidationError(
            "The uploaded XLSX file is not a valid Excel workbook."
        ) from None

"""Value-only CSV and XLSX parsing with source-row preservation."""

import csv
import io
from dataclasses import dataclass, field
from pathlib import PurePath
from typing import Any
from zipfile import BadZipFile, ZipFile

from openpyxl import load_workbook


SUPPORTED_EXTENSIONS = {".csv", ".xlsx"}
CSV_ENCODINGS = ("utf-8-sig", "utf-8", "cp1252")


class ParserError(ValueError):
    """Raised when a file cannot be parsed safely."""


@dataclass(frozen=True)
class ParsedRow:
    """One source row, retaining its original values and position."""

    source_row_number: int
    raw_row: dict[str, Any]
    sheet_name: str | None = None


@dataclass(frozen=True)
class ParseIssue:
    """A parsing problem tied to a source row or worksheet."""

    message: str
    source_row_number: int | None = None
    sheet_name: str | None = None
    raw_values: tuple[Any, ...] = ()


@dataclass
class ParseResult:
    """Rows and issues produced by parsing one uploaded file."""

    filename: str
    rows: list[ParsedRow] = field(default_factory=list)
    issues: list[ParseIssue] = field(default_factory=list)
    sheets: list[str] = field(default_factory=list)
    encoding: str | None = None


def parse_uploaded_file(filename: str, content: bytes) -> ParseResult:
    """Parse CSV or XLSX without normalising financial values."""

    if not filename or not filename.strip():
        raise ParserError("A filename is required.")

    safe_name = PurePath(filename.replace("\\", "/")).name

    if safe_name != filename or safe_name in {".", ".."}:
        raise ParserError("Invalid filename.")

    extension = PurePath(safe_name).suffix.lower()

    if extension in {".xlsm", ".xltm"}:
        raise ParserError("Macro-enabled Excel files are not supported.")

    if extension not in SUPPORTED_EXTENSIONS:
        raise ParserError("Only CSV and XLSX files are supported.")

    if not isinstance(content, bytes) or not content:
        return ParseResult(
            filename=safe_name,
            issues=[ParseIssue("The file is empty.")],
        )

    if extension == ".csv":
        return _parse_csv(safe_name, content)

    return _parse_xlsx(safe_name, content)


def _decode_csv(content: bytes) -> tuple[str, str]:
    """Decode CSV using supported encodings."""

    for encoding in CSV_ENCODINGS:
        try:
            return content.decode(encoding), encoding
        except UnicodeDecodeError:
            continue

    raise ParserError(
        "CSV encoding is unsupported. Use UTF-8 or Windows-1252."
    )


def _trim_trailing_empty_cells(values: tuple) -> tuple:
    """Remove Excel's trailing None padding, preserving populated cells."""

    values = list(values)

    while values and values[-1] is None:
        values.pop()

    return tuple(values)


def _validate_headers(
    headers: list[str],
    sheet_name: str | None = None,
) -> ParseIssue | None:
    """Check that headers are present, non-empty and unique."""

    cleaned = [str(value).strip() for value in headers]

    if not cleaned or not any(cleaned):
        return ParseIssue(
            "The source does not contain a valid header row.",
            source_row_number=1,
            sheet_name=sheet_name,
            raw_values=tuple(headers),
        )

    if any(not value for value in cleaned):
        return ParseIssue(
            "The header row contains an empty column name.",
            source_row_number=1,
            sheet_name=sheet_name,
            raw_values=tuple(headers),
        )

    if len(set(cleaned)) != len(cleaned):
        return ParseIssue(
            "The header row contains duplicate column names.",
            source_row_number=1,
            sheet_name=sheet_name,
            raw_values=tuple(headers),
        )

    return None


def _parse_csv(filename: str, content: bytes) -> ParseResult:
    """Parse CSV while preserving source line numbers."""

    text, encoding = _decode_csv(content)
    result = ParseResult(filename=filename, encoding=encoding)

    if "\x00" in text:
        raise ParserError("CSV contains invalid null characters.")

    reader = csv.reader(io.StringIO(text, newline=""), strict=True)

    try:
        headers = next(reader, None)

        if headers is None:
            result.issues.append(
                ParseIssue("The CSV file does not contain a header row.")
            )
            return result

        header_issue = _validate_headers(headers)

        if header_issue:
            result.issues.append(header_issue)
            return result

        headers = [str(value).strip() for value in headers]
        previous_line_number = reader.line_num

        while True:
            try:
                values = next(reader)
            except StopIteration:
                break
            except csv.Error as exc:
                result.issues.append(
                    ParseIssue(
                        f"Malformed CSV row: {exc}",
                        source_row_number=reader.line_num or None,
                    )
                )
                break

            source_row_number = previous_line_number + 1
            previous_line_number = reader.line_num

            if not values or not any(str(v).strip() for v in values):
                continue

            if len(values) != len(headers):
                result.issues.append(
                    ParseIssue(
                        message=(
                            f"Row has {len(values)} values; "
                            f"expected {len(headers)}."
                        ),
                        source_row_number=source_row_number,
                        raw_values=tuple(values),
                    )
                )
                continue

            result.rows.append(
                ParsedRow(
                    source_row_number=source_row_number,
                    raw_row=dict(zip(headers, values)),
                )
            )

    except csv.Error as exc:
        result.issues.append(ParseIssue(f"Malformed CSV file: {exc}"))

    return result


def _parse_xlsx(filename: str, content: bytes) -> ParseResult:
    """Parse every worksheet while preserving source row positions."""

    result = ParseResult(filename=filename)

    try:
        with ZipFile(io.BytesIO(content)) as archive:
            names = set(archive.namelist())

            if (
                "[Content_Types].xml" not in names
                or "xl/workbook.xml" not in names
            ):
                raise ParserError("The XLSX file is not a valid workbook.")

            if any(
                name.lower().endswith("vbaproject.bin")
                for name in names
            ):
                raise ParserError(
                    "Macro-enabled Excel content is not supported."
                )

            if archive.testzip() is not None:
                raise ParserError("The XLSX archive is corrupted.")

        workbook = load_workbook(
            io.BytesIO(content),
            read_only=True,
            data_only=True,
            keep_links=False,
        )

    except ParserError:
        raise
    except (BadZipFile, OSError, ValueError) as exc:
        raise ParserError("The XLSX file could not be opened.") from exc

    try:
        for worksheet in workbook.worksheets:
            sheet_name = worksheet.title
            result.sheets.append(sheet_name)
            iterator = worksheet.iter_rows(values_only=True)

            headers = next(iterator, None)

            if headers is None:
                result.issues.append(
                    ParseIssue(
                        "Worksheet is empty.",
                        sheet_name=sheet_name,
                    )
                )
                continue

            headers = _trim_trailing_empty_cells(headers)

            header_values = [
                "" if value is None else str(value).strip()
                for value in headers
            ]

            header_issue = _validate_headers(
                header_values,
                sheet_name=sheet_name,
            )

            if header_issue:
                result.issues.append(header_issue)
                continue

            for source_row_number, values in enumerate(iterator, start=2):
                values = _trim_trailing_empty_cells(values)

                if not any(
                    value is not None and str(value).strip()
                    for value in values
                ):
                    continue

                if len(values) != len(header_values):
                    result.issues.append(
                        ParseIssue(
                            message=(
                                f"Row has {len(values)} values; "
                                f"expected {len(header_values)}."
                            ),
                            source_row_number=source_row_number,
                            sheet_name=sheet_name,
                            raw_values=values,
                        )
                    )
                    continue

                result.rows.append(
                    ParsedRow(
                        source_row_number=source_row_number,
                        raw_row=dict(zip(header_values, values)),
                        sheet_name=sheet_name,
                    )
                )

    finally:
        workbook.close()

    if not result.sheets:
        result.issues.append(
            ParseIssue("The workbook does not contain any worksheets.")
        )

    return result

"""Required-field and row-level validation for parsed transaction records."""

from dataclasses import dataclass, field
from typing import Any, Iterable

from app.ingestion.csv_xlsx_parser import ParsedRow
from app.ingestion.header_mapper import (
    HeaderMappingResult,
    MappingIssue,
    map_row,
)


@dataclass(frozen=True)
class RowValidationIssue:
    code: str
    message: str
    field: str
    source_row_number: int
    sheet_name: str | None = None


@dataclass
class ValidatedRow:
    source_row_number: int
    sheet_name: str | None
    raw_row: dict[str, Any]
    canonical_row: dict[str, Any]
    issues: list[RowValidationIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.issues


@dataclass
class ValidationResult:
    rows: list[ValidatedRow] = field(default_factory=list)
    mapping_issues: list[MappingIssue] = field(default_factory=list)

    @property
    def valid_count(self) -> int:
        return sum(row.is_valid for row in self.rows)

    @property
    def invalid_count(self) -> int:
        return sum(not row.is_valid for row in self.rows)


def validate_parsed_rows(
    parsed_rows: Iterable[ParsedRow],
    mapping: HeaderMappingResult,
) -> ValidationResult:
    """Validate parsed rows without changing values or dropping invalid rows."""

    result = ValidationResult(mapping_issues=list(mapping.issues))

    # A structurally invalid mapping must not be used to validate data.
    if not mapping.is_valid:
        return result

    for parsed in parsed_rows:
        canonical = map_row(parsed.raw_row, mapping)
        issues: list[RowValidationIssue] = []

        for required_field in ("txn_date", "amount"):
            value = canonical.get(required_field)

            if value is None or not str(value).strip():
                issues.append(
                    RowValidationIssue(
                        code="MISSING_REQUIRED_VALUE",
                        message=(
                            f"Required value '{required_field}' is missing "
                            "or empty."
                        ),
                        field=required_field,
                        source_row_number=parsed.source_row_number,
                        sheet_name=parsed.sheet_name,
                    )
                )

        result.rows.append(
            ValidatedRow(
                source_row_number=parsed.source_row_number,
                sheet_name=parsed.sheet_name,
                raw_row=dict(parsed.raw_row),
                canonical_row=canonical,
                issues=issues,
            )
        )

    return result

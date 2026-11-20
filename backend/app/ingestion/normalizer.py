
"""Canonical transaction value normalisation.

Raw source values are never modified. Financial amounts use Decimal only.
"""

import re
from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone, tzinfo
from decimal import Decimal, InvalidOperation
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.models.enums import TransactionDirection


@dataclass(frozen=True)
class NormalizationIssue:
    code: str
    message: str
    field: str


@dataclass
class NormalizedRow:
    """Canonical values alongside the untouched source row."""

    source_row_number: int
    sheet_name: str | None
    raw_row: dict[str, Any]
    canonical_row: dict[str, Any] = field(default_factory=dict)
    issues: list[NormalizationIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.issues


@dataclass
class NormalizationResult:
    rows: list[NormalizedRow] = field(default_factory=list)

    @property
    def valid_count(self) -> int:
        return sum(row.is_valid for row in self.rows)

    @property
    def invalid_count(self) -> int:
        return sum(not row.is_valid for row in self.rows)


DATE_FORMATS = (
    "%Y-%m-%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%Y/%m/%d",
    "%d-%b-%Y",
    "%d %b %Y",
)

DIRECTION_ALIASES = {
    "CREDIT": TransactionDirection.CREDIT,
    "CR": TransactionDirection.CREDIT,
    "C": TransactionDirection.CREDIT,
    "DEBIT": TransactionDirection.DEBIT,
    "DR": TransactionDirection.DEBIT,
    "D": TransactionDirection.DEBIT,
}


def _resolve_timezone(source_timezone: str | tzinfo | None) -> tzinfo | None:
    """Resolve an explicitly supplied source timezone."""

    if source_timezone is None:
        return None

    if isinstance(source_timezone, tzinfo):
        return source_timezone

    if isinstance(source_timezone, str) and source_timezone.strip():
        try:
            return ZoneInfo(source_timezone.strip())
        except ZoneInfoNotFoundError as exc:
            raise ValueError(
                f"Unknown source timezone: {source_timezone!r}"
            ) from exc

    raise ValueError("Source timezone must be a valid timezone name or tzinfo.")


def normalize_date(
    value: Any,
    source_timezone: str | tzinfo | None = None,
) -> datetime:
    """Parse a date/time and return a UTC-aware datetime."""

    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime.combine(value, time.min)
    elif isinstance(value, str):
        cleaned = value.strip()

        if not cleaned:
            raise ValueError("Transaction date is empty.")

        parsed = None

        try:
            parsed = datetime.fromisoformat(
                cleaned.replace("Z", "+00:00")
            )
        except ValueError:
            pass

        if parsed is None:
            for date_format in DATE_FORMATS:
                try:
                    parsed = datetime.strptime(cleaned, date_format)
                    break
                except ValueError:
                    continue

        if parsed is None:
            raise ValueError(
                f"Unsupported transaction date format: {value!r}"
            )
    else:
        raise ValueError("Transaction date must be a date, datetime or string.")

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        resolved_timezone = _resolve_timezone(source_timezone)

        if resolved_timezone is None:
            raise ValueError(
                "Transaction date has no timezone. "
                "Provide the source timezone explicitly."
            )

        parsed = parsed.replace(tzinfo=resolved_timezone)

    return parsed.astimezone(timezone.utc)


def normalize_amount(value: Any) -> tuple[Decimal, TransactionDirection]:
    """Return a positive Decimal magnitude and direction from the sign."""

    if isinstance(value, bool) or isinstance(value, float):
        raise ValueError(
            "Financial amounts must not use binary floating-point."
        )

    if isinstance(value, Decimal):
        amount = value
    elif isinstance(value, int):
        amount = Decimal(value)
    elif isinstance(value, str):
        cleaned = value.strip()

        if not cleaned:
            raise ValueError("Transaction amount is empty.")

        # Accept conventional comma-separated thousands groups.
        if "," in cleaned:
            if not re.fullmatch(
                r"[+-]?(?:\d{1,3}(?:,\d{3})+)(?:\.\d+)?",
                cleaned,
            ):
                raise ValueError("Transaction amount has invalid separators.")
            cleaned = cleaned.replace(",", "")

        try:
            amount = Decimal(cleaned)
        except InvalidOperation as exc:
            raise ValueError("Transaction amount is not a valid decimal.") from exc
    else:
        raise ValueError(
            "Transaction amount must be a Decimal, integer or decimal string."
        )

    if not amount.is_finite():
        raise ValueError("Transaction amount must be finite.")

    direction = (
        TransactionDirection.DEBIT
        if amount < 0
        else TransactionDirection.CREDIT
    )

    return abs(amount), direction


def normalize_direction(value: Any) -> TransactionDirection:
    """Normalise an explicitly supplied direction value."""

    if isinstance(value, TransactionDirection):
        return value

    if not isinstance(value, str) or not value.strip():
        raise ValueError("Transaction direction is empty or invalid.")

    direction = DIRECTION_ALIASES.get(value.strip().upper())

    if direction is None:
        raise ValueError(
            f"Unsupported transaction direction: {value!r}. "
            "Use CREDIT/CR or DEBIT/DR."
        )

    return direction


def normalize_currency(value: Any) -> str:
    """Normalise a three-letter currency code without performing FX conversion."""

    if not isinstance(value, str):
        raise ValueError("Currency must be a three-letter code.")

    currency = value.strip().upper()

    if not re.fullmatch(r"[A-Z]{3}", currency):
        raise ValueError(
            "Currency must contain exactly three alphabetic characters."
        )

    return currency


def normalize_reference(value: Any) -> str | None:
    """Trim and uppercase a reference while preserving the original raw value."""

    if value is None:
        return None

    reference = str(value).strip()

    if not reference:
        return None

    return reference.upper()


def normalize_row(
    validated_row: Any,
    source_timezone: str | tzinfo | None = None,
) -> NormalizedRow:
    """Normalise one validated row and retain all original source values."""

    result = NormalizedRow(
        source_row_number=validated_row.source_row_number,
        sheet_name=validated_row.sheet_name,
        raw_row=dict(validated_row.raw_row),
    )

    if not validated_row.is_valid:
        result.issues.append(
            NormalizationIssue(
                code="UPSTREAM_VALIDATION_FAILED",
                message="This row contains validation issues and cannot be normalised.",
                field="row",
            )
        )
        return result

    source = validated_row.canonical_row

    try:
        result.canonical_row["txn_date"] = normalize_date(
            source.get("txn_date"),
            source_timezone,
        )
    except (ValueError, TypeError) as exc:
        result.issues.append(
            NormalizationIssue("INVALID_DATE", str(exc), "txn_date")
        )

    amount_direction = None

    try:
        amount, amount_direction = normalize_amount(source.get("amount"))
        result.canonical_row["amount"] = amount
    except (ValueError, TypeError) as exc:
        result.issues.append(
            NormalizationIssue("INVALID_AMOUNT", str(exc), "amount")
        )

    explicit_direction = source.get("direction")

    if explicit_direction is not None and str(explicit_direction).strip():
        try:
            direction = normalize_direction(explicit_direction)

            if (
                amount_direction is not None
                and amount != 0
                and direction != amount_direction
            ):
                raise ValueError(
                    "Explicit direction conflicts with the signed amount."
                )

            result.canonical_row["direction"] = direction
        except (ValueError, TypeError) as exc:
            result.issues.append(
                NormalizationIssue("INVALID_DIRECTION", str(exc), "direction")
            )
    elif amount_direction is not None:
        result.canonical_row["direction"] = amount_direction
    else:
        result.issues.append(
            NormalizationIssue(
                "MISSING_DIRECTION",
                "Direction cannot be determined because the amount is invalid.",
                "direction",
            )
        )

    currency_value = source.get("currency")

    if currency_value is not None and str(currency_value).strip():
        try:
            result.canonical_row["currency"] = normalize_currency(
                currency_value
            )
        except (ValueError, TypeError) as exc:
            result.issues.append(
                NormalizationIssue("INVALID_CURRENCY", str(exc), "currency")
            )
    else:
        result.issues.append(
            NormalizationIssue(
                "MISSING_CURRENCY",
                "Currency is required for a canonical transaction.",
                "currency",
            )
        )

    for field_name in ("txn_ref", "reference_norm"):
        if field_name in source:
            result.canonical_row[field_name] = normalize_reference(
                source[field_name]
            )

    if "description" in source:
        description = source["description"]
        result.canonical_row["description_raw"] = (
            None if description is None else str(description)
        )
        result.canonical_row["description_norm"] = (
            None
            if description is None or not str(description).strip()
            else " ".join(str(description).split()).casefold()
        )

    return result


def normalize_rows(
    validated_rows: list[Any],
    source_timezone: str | tzinfo | None = None,
) -> NormalizationResult:
    """Normalise a collection of validated rows without dropping failures."""

    result = NormalizationResult()

    for row in validated_rows:
        result.rows.append(normalize_row(row, source_timezone))

    return result

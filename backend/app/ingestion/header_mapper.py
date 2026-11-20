
"""Source-specific transaction header mapping for bank, ledger and gateway files."""

import re
from dataclasses import dataclass, field

from app.models.enums import SourceType


class HeaderMappingError(ValueError):
    """Raised when a source type or header configuration is invalid."""


@dataclass(frozen=True)
class MappingIssue:
    code: str
    message: str
    header: str | None = None


@dataclass
class HeaderMappingResult:
    source_type: SourceType
    field_map: dict[str, str] = field(default_factory=dict)
    unknown_headers: list[str] = field(default_factory=list)
    issues: list[MappingIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.issues


# Canonical field -> accepted source column names.
# Aliases are deliberately explicit; no fuzzy guessing is performed.
COMMON_ALIASES = {
    "txn_ref": {
        "transaction_id", "transaction id", "txn_id", "txn id",
        "transaction_reference", "transaction reference",
        "payment_id", "payment id", "order_id", "order id",
    },
    "txn_date": {
        "transaction_date", "transaction date", "txn_date", "txn date",
        "date", "posting_date", "posting date", "value_date",
        "value date", "payment_date", "payment date",
    },
    "description": {
        "description", "transaction_description",
        "transaction description", "narration", "details",
        "remarks", "memo",
    },
    "amount": {
        "amount", "transaction_amount", "transaction amount",
        "txn_amount", "txn amount", "net_amount", "net amount",
    },
    "currency": {
        "currency", "currency_code", "currency code", "ccy",
    },
    "reference_norm": {
        "reference", "reference_number", "reference number",
        "ref", "ref_no", "ref no", "utr", "rrn",
        "bank_reference", "bank reference",
        "payment_reference", "payment reference",
        "gateway_reference", "gateway reference",
    },
    "direction": {
        "direction", "transaction_type", "transaction type",
        "dr_cr", "dr/cr", "debit_credit", "debit/credit",
    },
}

SOURCE_ALIASES = {
    SourceType.BANK: {
        **COMMON_ALIASES,
        "txn_ref": COMMON_ALIASES["txn_ref"] | {
            "bank_transaction_id", "bank transaction id",
        },
        "reference_norm": COMMON_ALIASES["reference_norm"] | {
            "utr_number", "utr number", "cheque_reference",
            "cheque reference",
        },
    },
    SourceType.LEDGER: {
        **COMMON_ALIASES,
        "txn_ref": COMMON_ALIASES["txn_ref"] | {
            "journal_id", "journal id", "voucher_number",
            "voucher number", "document_number", "document number",
        },
        "reference_norm": COMMON_ALIASES["reference_norm"] | {
            "journal_reference", "journal reference",
            "voucher_reference", "voucher reference",
        },
    },
    SourceType.GATEWAY: {
        **COMMON_ALIASES,
        "txn_ref": COMMON_ALIASES["txn_ref"] | {
            "gateway_transaction_id", "gateway transaction id",
            "payment_intent_id", "payment intent id",
        },
        "reference_norm": COMMON_ALIASES["reference_norm"] | {
            "settlement_id", "settlement id", "batch_id", "batch id",
            "rrn_number", "rrn number",
        },
    },
}

REQUIRED_FIELDS = {"txn_date", "amount"}


def _normalise_header(value: str) -> str:
    """Normalise header spelling without guessing its meaning."""
    cleaned = str(value).strip().lower()
    cleaned = re.sub(r"[\s\-]+", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned)
    return cleaned


def map_headers(
    headers: list[str],
    source_type: SourceType | str,
) -> HeaderMappingResult:
    """Map source headers to canonical transaction field names."""

    try:
        source = (
            source_type
            if isinstance(source_type, SourceType)
            else SourceType(str(source_type).upper())
        )
    except ValueError as exc:
        raise HeaderMappingError(
            f"Unsupported source type: {source_type!r}. "
            "Expected BANK, LEDGER or GATEWAY."
        ) from exc

    if not headers:
        raise HeaderMappingError("At least one source header is required.")

    aliases = SOURCE_ALIASES[source]
    alias_lookup: dict[str, str] = {}

    for canonical_field, names in aliases.items():
        for alias in names | {canonical_field}:
            alias_lookup[_normalise_header(alias)] = canonical_field

    result = HeaderMappingResult(source_type=source)
    mapped_sources: dict[str, str] = {}

    for original_header in headers:
        if not isinstance(original_header, str) or not original_header.strip():
            result.issues.append(
                MappingIssue(
                    code="EMPTY_HEADER",
                    message="A source column has an empty header.",
                    header=str(original_header),
                )
            )
            continue

        normalised = _normalise_header(original_header)
        canonical = alias_lookup.get(normalised)

        if canonical is None:
            result.unknown_headers.append(original_header)
            result.issues.append(
                MappingIssue(
                    code="UNKNOWN_HEADER",
                    message=(
                        f"Column '{original_header}' is not recognised for "
                        f"{source.value}. Add an approved alias or correct "
                        "the source header."
                    ),
                    header=original_header,
                )
            )
            continue

        if canonical in mapped_sources:
            previous = mapped_sources[canonical]
            result.issues.append(
                MappingIssue(
                    code="AMBIGUOUS_HEADER",
                    message=(
                        f"Both '{previous}' and '{original_header}' map to "
                        f"'{canonical}'. Keep only one source column or "
                        "configure an explicit mapping."
                    ),
                    header=original_header,
                )
            )
            continue

        mapped_sources[canonical] = original_header
        result.field_map[canonical] = original_header

    for required_field in sorted(REQUIRED_FIELDS):
        if required_field not in result.field_map:
            result.issues.append(
                MappingIssue(
                    code="MISSING_REQUIRED_HEADER",
                    message=(
                        f"Required column '{required_field}' is missing "
                        f"for {source.value}. Provide a recognised date "
                        "or amount header."
                    ),
                    header=required_field,
                )
            )

    return result


def map_row(
    raw_row: dict,
    mapping: HeaderMappingResult,
) -> dict:
    """Return canonical field names while preserving the original row elsewhere."""
    return {
        canonical: raw_row[source_header]
        for canonical, source_header in mapping.field_map.items()
        if source_header in raw_row
    }


"""Source provenance and deterministic transaction fingerprints."""

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from app.models.enums import SourceType


@dataclass(frozen=True)
class RowProvenance:
    source_filename: str
    source_type: SourceType
    source_row_number: int
    sheet_name: str | None
    raw_row: dict[str, Any]
    raw_sha256: str


def _json_default(value: Any) -> str:
    """Convert supported source values into stable JSON representations."""

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, Decimal):
        return str(value)

    if isinstance(value, Enum):
        return value.value

    return str(value)


def _stable_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=_json_default,
    )


def create_provenance(
    filename: str,
    source_type: SourceType | str,
    source_row_number: int,
    raw_row: dict[str, Any],
    sheet_name: str | None = None,
) -> RowProvenance:
    """Create immutable source-location metadata and a raw-row hash."""

    if not isinstance(filename, str) or not filename.strip():
        raise ValueError("A source filename is required.")

    if (
        isinstance(source_row_number, bool)
        or not isinstance(source_row_number, int)
        or source_row_number < 1
    ):
        raise ValueError("Source row number must be a positive integer.")

    try:
        resolved_source = (
            source_type
            if isinstance(source_type, SourceType)
            else SourceType(str(source_type).upper())
        )
    except ValueError as exc:
        raise ValueError("Source type must be BANK, LEDGER or GATEWAY.") from exc

    if not isinstance(raw_row, dict):
        raise ValueError("Raw source row must be a dictionary.")

    raw_copy = dict(raw_row)
    raw_sha256 = hashlib.sha256(
        _stable_json(raw_copy).encode("utf-8")
    ).hexdigest()

    return RowProvenance(
        source_filename=filename.strip(),
        source_type=resolved_source,
        source_row_number=source_row_number,
        sheet_name=sheet_name,
        raw_row=raw_copy,
        raw_sha256=raw_sha256,
    )


def create_transaction_fingerprint(
    provenance: RowProvenance,
    canonical_row: dict[str, Any],
) -> str:
    """Create a deterministic fingerprint from source identity and canonical data."""

    if not isinstance(provenance, RowProvenance):
        raise TypeError("A RowProvenance instance is required.")

    if not isinstance(canonical_row, dict):
        raise ValueError("Canonical row must be a dictionary.")

    fingerprint_payload = {
        "source_filename": provenance.source_filename,
        "source_type": provenance.source_type.value,
        "source_row_number": provenance.source_row_number,
        "sheet_name": provenance.sheet_name,
        "raw_sha256": provenance.raw_sha256,
        "canonical_row": canonical_row,
    }

    return hashlib.sha256(
        _stable_json(fingerprint_payload).encode("utf-8")
    ).hexdigest()

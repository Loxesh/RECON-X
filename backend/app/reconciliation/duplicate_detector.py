
"""Create a file-provenance-independent SHA-256 fingerprint.

    The fingerprint uses source type, date, amount, currency, reference and
    narrative. It deliberately excludes file name, row number and internal
    transaction ID so the same source transaction can be detected across files.
    """

import hashlib
import json
from dataclasses import dataclass
from datetime import timezone
from decimal import Decimal
from enum import Enum
from typing import Iterable

from app.reconciliation.schemas import MatchingTransaction


class DuplicateClassification(str, Enum):
    DUPLICATE = "DUPLICATE"
    REFERENCE_CONFLICT = "REFERENCE_CONFLICT"


@dataclass(frozen=True)
class DuplicateEvidence:
    classification: DuplicateClassification
    fingerprint: str
    transaction_ids: tuple[str, ...]
    source_type: str
    reason: str
    compared_fields: tuple[str, ...]
    observed_values: tuple[tuple[str, str], ...]


def _validate_transaction(transaction: MatchingTransaction) -> None:
    value = transaction.transaction_date

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(
            "Duplicate detection requires timezone-aware transaction dates."
        )

    if value.utcoffset() != timezone.utc.utcoffset(value):
        raise ValueError(
            "Transaction dates must be normalized to UTC before duplicate detection."
        )


def _normalise(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.casefold().split())


def _canonical_amount(amount: Decimal) -> str:
    return format(amount.normalize(), "f")


def create_duplicate_fingerprint(
    transaction: MatchingTransaction,
) -> str:
    """Create a source-independent SHA-256 fingerprint for duplicate detection.

    The fingerprint uses source, date, amount, currency, reference and
    narrative. It deliberately excludes file name, row number and internal
    transaction ID so the same source transaction can be detected across files.
    """

    _validate_transaction(transaction)

    reference = _normalise(
        transaction.reference_norm or transaction.transaction_reference
    )

    if not reference:
        raise ValueError(
            "A stable transaction reference is required to create a "
            "duplicate fingerprint. Amount/date alone are insufficient."
        )

    payload = {
        "source_type": transaction.source_type.value,
        "transaction_date": transaction.transaction_date.date().isoformat(),
        "amount": _canonical_amount(transaction.amount),
        "currency": transaction.currency,
        "reference": reference,
        "narrative": _normalise(transaction.description_norm),
    }

    canonical_json = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def detect_duplicates(
    transactions: Iterable[MatchingTransaction],
) -> tuple[DuplicateEvidence, ...]:
    """Find exact canonical duplicates within and across supplied source files.

    Transactions with the same reference but different canonical fingerprints
    are reported as reference conflicts, not automatically deleted or merged.

    Repeated same-value payments with different references are not duplicates.
    """

    items = tuple(transactions)

    transaction_ids = [item.transaction_id for item in items]
    if len(transaction_ids) != len(set(transaction_ids)):
        raise ValueError(
            "Duplicate detection input must contain unique internal transaction IDs."
        )

    for transaction in items:
        _validate_transaction(transaction)

    fingerprint_groups: dict[str, list[MatchingTransaction]] = {}
    reference_groups: dict[
        tuple[str, str], list[MatchingTransaction]
    ] = {}

    for transaction in items:
        reference = _normalise(
            transaction.reference_norm or transaction.transaction_reference
        )

        if not reference:
            continue

        fingerprint = create_duplicate_fingerprint(transaction)

        fingerprint_groups.setdefault(fingerprint, []).append(transaction)

        reference_groups.setdefault(
            (transaction.source_type.value, reference), []
        ).append(transaction)

    findings: list[DuplicateEvidence] = []

    for fingerprint, group in fingerprint_groups.items():
        if len(group) < 2:
            continue

        ordered = sorted(group, key=lambda item: item.transaction_id)

        findings.append(
            DuplicateEvidence(
                classification=DuplicateClassification.DUPLICATE,
                fingerprint=fingerprint,
                transaction_ids=tuple(
                    item.transaction_id for item in ordered
                ),
                source_type=ordered[0].source_type.value,
                reason=(
                    "Transactions share the same canonical source, date, amount, "
                    "currency, reference and narrative fingerprint."
                ),
                compared_fields=(
                    "source_type",
                    "transaction_date",
                    "amount",
                    "currency",
                    "reference",
                    "description_norm",
                ),
                observed_values=(
                    ("transaction_date", ordered[0].transaction_date.date().isoformat()),
                    ("amount", str(ordered[0].amount)),
                    ("currency", ordered[0].currency),
                    (
                        "reference",
                        _normalise(
                            ordered[0].reference_norm
                            or ordered[0].transaction_reference
                        ),
                    ),
                    (
                        "narrative",
                        _normalise(ordered[0].description_norm),
                    ),
                    ("group_size", str(len(ordered))),
                ),
            )
        )

    for (source_type, reference), group in reference_groups.items():
        distinct_fingerprints = {
            create_duplicate_fingerprint(item) for item in group
        }

        if len(group) < 2 or len(distinct_fingerprints) == 1:
            continue

        ordered = sorted(group, key=lambda item: item.transaction_id)

        findings.append(
            DuplicateEvidence(
                classification=DuplicateClassification.REFERENCE_CONFLICT,
                fingerprint="",
                transaction_ids=tuple(
                    item.transaction_id for item in ordered
                ),
                source_type=source_type,
                reason=(
                    "The same source reference appears with different "
                    "canonical transaction details. This requires investigation "
                    "and is not classified as a confirmed duplicate."
                ),
                compared_fields=(
                    "source_type",
                    "reference",
                    "transaction_date",
                    "amount",
                    "currency",
                    "description_norm",
                ),
                observed_values=(
                    ("reference", reference),
                    (
                        "fingerprint_count",
                        str(len(distinct_fingerprints)),
                    ),
                    ("group_size", str(len(ordered))),
                ),
            )
        )

    findings.sort(
        key=lambda item: (
            item.classification.value,
            item.source_type,
            item.transaction_ids,
        )
    )

    return tuple(findings)

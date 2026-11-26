"""Evidence-reference integrity checks for LLM-generated explanations."""

from collections.abc import Collection, Iterable


class EvidenceReferenceError(ValueError):
    """Raised when evidence references are invalid or unsupported."""


def validate_evidence_references(
    referenced_ids: Iterable[str],
    allowed_ids: Collection[str],
) -> frozenset[str]:
    """Ensure every referenced record ID belongs to the supplied evidence."""

    if isinstance(referenced_ids, (str, bytes)):
        raise EvidenceReferenceError(
            "Referenced evidence IDs must be an iterable of record IDs."
        )

    if isinstance(allowed_ids, (str, bytes)):
        raise EvidenceReferenceError(
            "Allowed evidence IDs must be a collection of record IDs."
        )

    try:
        references = list(referenced_ids)
        allowed = set(allowed_ids)
    except TypeError as exc:
        raise EvidenceReferenceError(
            "Evidence references must be valid collections."
        ) from exc

    if not allowed:
        raise EvidenceReferenceError("No allowed evidence records were supplied.")

    if any(
        not isinstance(record_id, str) or not record_id.strip()
        for record_id in allowed
    ):
        raise EvidenceReferenceError("Allowed evidence contains an invalid record ID.")

    if any(
        not isinstance(record_id, str) or not record_id.strip()
        for record_id in references
    ):
        raise EvidenceReferenceError("Referenced evidence contains an invalid ID.")

    if len(references) != len(set(references)):
        raise EvidenceReferenceError("Duplicate evidence references are not allowed.")

    if set(references) - allowed:
        raise EvidenceReferenceError(
            "One or more evidence references were not supplied."
        )

    return frozenset(references)


def validate_claim_evidence(
    claims: Iterable[object],
    allowed_ids: Collection[str],
) -> frozenset[str]:
    """Validate evidence IDs across claim objects exposing evidence_record_ids."""

    if isinstance(claims, (str, bytes)):
        raise EvidenceReferenceError("Claims must be an iterable of claim objects.")

    try:
        claim_list = list(claims)
    except TypeError as exc:
        raise EvidenceReferenceError("Claims must be iterable.") from exc

    if not claim_list:
        raise EvidenceReferenceError("At least one evidence-backed claim is required.")

    all_references: set[str] = set()

    for claim in claim_list:
        evidence_ids = getattr(claim, "evidence_record_ids", None)

        if evidence_ids is None or isinstance(evidence_ids, (str, bytes)):
            raise EvidenceReferenceError(
                "A claim must provide evidence_record_ids as a collection."
            )

        try:
            claim_ids = list(evidence_ids)
        except TypeError as exc:
            raise EvidenceReferenceError(
                "Claim evidence IDs must be iterable."
            ) from exc

        if not claim_ids:
            raise EvidenceReferenceError(
                "Every claim must reference at least one evidence record."
            )

        validated = validate_evidence_references(claim_ids, allowed_ids)
        all_references.update(validated)

    return frozenset(all_references)


"""Validation helpers for human approval decisions."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.models.enums import ApprovalDecision


class ApprovalWorkflowError(ValueError):
    """Raised when an approval decision is invalid."""


def validate_decision(
    decision: ApprovalDecision,
    comment: str | None,
    after: dict[str, Any] | None,
) -> None:
    """Validate the decision-specific requirements."""

    if not isinstance(decision, ApprovalDecision):
        raise ApprovalWorkflowError("Invalid approval decision.")

    if comment is not None:
        if not isinstance(comment, str) or len(comment) > 4000:
            raise ApprovalWorkflowError("Comment must not exceed 4000 characters.")

    if decision == ApprovalDecision.MODIFY:
        if not isinstance(after, dict) or not after:
            raise ApprovalWorkflowError(
                "A non-empty modification payload is required."
            )

    elif after:
        raise ApprovalWorkflowError(
            "Modification data is only accepted for a modify decision."
        )


def request_fingerprint(
    *,
    exception_id: str,
    decision: ApprovalDecision,
    comment: str | None,
    after: dict[str, Any] | None,
) -> str:
    """Return a stable SHA-256 fingerprint for an approval request."""

    payload = {
        "exception_id": exception_id,
        "decision": decision.value,
        "comment": comment,
        "after": after or {},
    }

    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )

    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

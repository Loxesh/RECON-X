
"""Application-facing audit logging service."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.governance.audit_repository import AuditRepository


class AuditLogger:
    """Create validated audit events through the audit repository."""

    def __init__(self, repository: AuditRepository):
        self.repository = repository

    def log(
        self,
        *,
        event_type: str,
        actor: dict[str, Any],
        resource: dict[str, Any],
        action: str,
        outcome: str,
        correlation_id: str,
        details: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
    ) -> dict[str, Any]:
        """Append one immutable audit event."""

        event = {
            "ts": timestamp or datetime.now(timezone.utc),
            "event_type": event_type,
            "actor": actor,
            "resource": resource,
            "action": action,
            "outcome": outcome,
            "details": details or {},
            "correlation_id": correlation_id,
        }

        return self.repository.append(event)

    def verify(self) -> dict[str, Any]:
        """Verify the tenant's complete audit hash chain."""

        return self.repository.verify_chain()

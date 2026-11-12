
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.base import TenantDocument
from app.models.enums import AuditOutcome


class AuditActor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actor_id: str | None = None
    actor_type: str = "USER"
    name: str | None = None


class AuditResource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resource_type: str
    resource_id: str


class AuditEventDocument(TenantDocument):
    seq: int = Field(ge=1)
    ts: datetime

    event_type: str = Field(min_length=1)
    actor: AuditActor
    resource: AuditResource

    action: str = Field(min_length=1)
    outcome: AuditOutcome

    details: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str = Field(min_length=1)

    prev_hash: str | None = None
    hash: str = Field(min_length=1)


from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.base import TenantDocument


class WorkflowStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    status: str = "PENDING"
    attempts: int = Field(default=0, ge=0)
    checkpoint: dict[str, Any] = Field(default_factory=dict)


class WorkflowRunDocument(TenantDocument):
    job_id: str = Field(min_length=1)

    state: str = "PENDING"
    plan: list[str] = Field(default_factory=list)
    steps: list[WorkflowStep] = Field(default_factory=list)

    correlation_id: str = Field(min_length=1)
    error: dict[str, Any] | None = None

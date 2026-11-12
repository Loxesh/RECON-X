
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.base import TenantDocument


class ReportSignoff(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = "PENDING"
    signed_by: str | None = None
    signed_at: str | None = None
    comment: str | None = None


class ReportDocument(TenantDocument):
    job_id: str = Field(min_length=1)
    format: str = Field(min_length=1)

    storage_key: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")

    figures_snapshot: dict[str, Any] = Field(default_factory=dict)
    narrative: str = ""

    generated_by: str = Field(min_length=1)
    signoff: ReportSignoff = Field(default_factory=ReportSignoff)


from datetime import datetime

from pydantic import Field

from app.schemas.common import ApiSchema


class ReportSignoffSchema(ApiSchema):
    """Human review and sign-off information."""

    status: str = "PENDING"
    signed_by: str | None = None
    signed_at: datetime | None = None
    comment: str | None = None


class ReportResponse(ApiSchema):
    """Report metadata returned to the frontend."""

    id: str
    job_id: str
    format: str

    sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")

    figures_snapshot: dict = Field(default_factory=dict)
    narrative: str = ""

    generated_by: str
    signoff: ReportSignoffSchema = Field(
        default_factory=ReportSignoffSchema
    )

    created_at: datetime


class ReportGenerationRequest(ApiSchema):
    """Request to generate a reconciliation report."""

    job_id: str = Field(min_length=1)
    format: str = Field(pattern=r"^(PDF|XLSX)$")


class ReportListFilters(ApiSchema):
    """Filters for retrieving generated reports."""

    job_id: str | None = None
    format: str | None = None
    signoff_status: str | None = None

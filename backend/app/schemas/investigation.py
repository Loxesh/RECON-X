
from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.common import ApiSchema


class InvestigationGenerator(ApiSchema):
    """Identifies the agent and LLM usage behind an investigation."""

    agent: str = Field(min_length=1)
    llm_usage_id: str | None = None


class InvestigationValidation(ApiSchema):
    """Validation outcome for an investigation result."""

    status: str = "PENDING"
    issues: list[str] = Field(default_factory=list)


class InvestigationResponse(ApiSchema):
    """Investigation findings returned by the API."""

    id: str
    exception_id: str
    version: int = Field(ge=1)

    findings: dict[str, Any] = Field(default_factory=dict)
    cited_record_ids: list[str] = Field(default_factory=list)
    explanation_text: str

    recommended_actions: list[str] = Field(default_factory=list)
    confidence_label: str

    generated_by: InvestigationGenerator
    validation: InvestigationValidation = Field(
        default_factory=InvestigationValidation
    )

    created_at: datetime


class InvestigationRequest(ApiSchema):
    """Request to initiate an investigation for an exception."""

    exception_id: str = Field(min_length=1)


class InvestigationListFilters(ApiSchema):
    """Filters for retrieving investigation records."""

    exception_id: str | None = None
    confidence_label: str | None = None
    validation_status: str | None = None

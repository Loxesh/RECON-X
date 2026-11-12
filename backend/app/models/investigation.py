
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.base import TenantDocument
from app.models.enums import ConfidenceLabel


class InvestigationGenerator(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent: str
    llm_usage_id: str | None = None


class InvestigationValidation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = "PENDING"
    issues: list[str] = Field(default_factory=list)


class InvestigationDocument(TenantDocument):
    exception_id: str = Field(min_length=1)
    version: int = Field(default=1, ge=1)

    findings: dict[str, Any] = Field(default_factory=dict)
    cited_record_ids: list[str] = Field(default_factory=list)

    explanation_text: str = ""
    recommended_actions: list[str] = Field(default_factory=list)

    confidence_label: ConfidenceLabel
    generated_by: InvestigationGenerator
    validation: InvestigationValidation = Field(
        default_factory=InvestigationValidation
    )

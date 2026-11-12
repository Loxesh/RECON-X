
from typing import Any

from pydantic import BaseModel, Field

from app.models.base import DocumentBase
from app.models.bson import Money


class MatchingRules(BaseModel):
    date_tolerance_days: int = Field(default=3, ge=0)
    amount_tolerance: Money = Money("0.00")
    reference_matching: bool = True


class RiskPolicy(BaseModel):
    high_risk_threshold: int = Field(default=70, ge=0, le=100)
    medium_risk_threshold: int = Field(default=40, ge=0, le=100)


class BudgetSettings(BaseModel):
    monthly_usd: Money = Money("0.00")
    per_job_usd: Money = Money("0.00")
    alert_pct: int = Field(default=80, ge=0, le=100)


class OrganizationSettings(BaseModel):
    matching_rules: MatchingRules = Field(default_factory=MatchingRules)
    risk_policy: RiskPolicy = Field(default_factory=RiskPolicy)
    retention_days: int = Field(default=365, ge=1)
    budget: BudgetSettings = Field(default_factory=BudgetSettings)
    maker_checker: bool = True
    base_currency: str = Field(default="INR", min_length=3, max_length=3)


class OrganizationDocument(DocumentBase):
    name: str = Field(min_length=2, max_length=150)
    slug: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    status: str = "ACTIVE"
    settings: OrganizationSettings = Field(
        default_factory=OrganizationSettings
    )

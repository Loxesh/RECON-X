
from decimal import Decimal

from pydantic import Field

from app.models.base import TenantDocument
from app.models.bson import Money


class LLMUsageDocument(TenantDocument):
    job_id: str = Field(min_length=1)
    agent_name: str = Field(min_length=1)
    task: str = Field(min_length=1)

    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    tier: str = Field(min_length=1)

    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)

    cached: bool = False
    est_cost: Money
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")
    price_version: str = Field(min_length=1)

    latency_ms: int = Field(ge=0)
    status: str = "SUCCESS"
    correlation_id: str = Field(min_length=1)

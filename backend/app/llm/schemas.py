
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.bson import Money


class LLMMessage(BaseModel):
    """A conversation message containing no privileged system policy."""

    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=100_000)


class LLMRequest(BaseModel):
    """Provider-neutral request with an explicitly separated trusted policy."""

    model_config = ConfigDict(extra="forbid")

    system_policy: str | None = Field(
        default=None,
        min_length=1,
        max_length=20_000,
        description=(
            "Trusted application-authored policy. Never populate this field "
            "with uploaded files, descriptions, historical notes, or other "
            "untrusted external content."
        ),
    )
    messages: list[LLMMessage] = Field(min_length=1, max_length=100)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_output_tokens: int = Field(default=1024, ge=1, le=8192)

    @field_validator("system_policy")
    @classmethod
    def validate_system_policy(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("System policy cannot be blank.")
        return value


class LLMUsageContext(BaseModel):
    """Trusted execution and pricing context supplied by the caller."""

    model_config = ConfigDict(extra="forbid")

    org_id: str = Field(min_length=1, max_length=128)
    job_id: str = Field(min_length=1, max_length=128)
    agent_name: str = Field(min_length=1, max_length=100)
    task: str = Field(min_length=1, max_length=100)
    tier: str = Field(default="standard", min_length=1, max_length=50)
    correlation_id: str = Field(min_length=1, max_length=128)
    estimated_cost: Money
    price_version: str = Field(min_length=1, max_length=64)
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")

    @field_validator("estimated_cost")
    @classmethod
    def validate_non_negative_cost(cls, value: Decimal) -> Decimal:
        if value < Decimal("0"):
            raise ValueError("Estimated cost cannot be negative.")
        return value


class LLMResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str
    provider: str
    model: str
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    latency_ms: int = Field(default=0, ge=0)
    fallback_used: bool = False

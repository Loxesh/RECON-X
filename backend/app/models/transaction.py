
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.base import TenantDocument
from app.models.bson import Money
from app.models.enums import (
    SourceType,
    TransactionDirection,
    TransactionValidity,
)


class TransactionValidationError(BaseModel):
    """A validation issue found in an imported transaction."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)


class TransactionDocument(TenantDocument):
    job_id: str = Field(min_length=1)
    file_id: str = Field(min_length=1)

    source_type: SourceType
    source_row: int = Field(ge=1)

    txn_ref: str | None = None
    reference_norm: str | None = None
    txn_date: datetime

    amount: Money
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    direction: TransactionDirection

    description_raw: str | None = None
    description_norm: str | None = None
    fingerprint: str = Field(min_length=1)

    validity: TransactionValidity
    validation_errors: list[TransactionValidationError] = Field(
        default_factory=list
    )

    raw_row: dict[str, Any] = Field(default_factory=dict)
    match_status: str = "UNMATCHED"
    flags: list[str] = Field(default_factory=list)

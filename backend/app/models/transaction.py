
from datetime import datetime
from typing import Any

from pydantic import Field

from app.models.base import TenantDocument
from app.models.bson import Money
from app.models.enums import (
    SourceType,
    TransactionDirection,
    TransactionValidity,
    TransactionMatchStatus,
)




class TransactionDocument(TenantDocument):
    job_id: str
    file_id: str
    source_type: SourceType
    source_row: int = Field(ge=1)

    txn_ref: str | None = None
    reference_norm: str | None = None
    txn_date: datetime

    amount: Money
    currency: str = Field(min_length=3, max_length=3)
    direction: TransactionDirection

    description_raw: str | None = None
    description_norm: str | None = None
    fingerprint: str

    validity: TransactionValidity = TransactionValidity.VALID
    validation_errors: list[dict[str, Any]] = Field(default_factory=list)
    raw_row: dict[str, Any] = Field(default_factory=dict)

    match_status: TransactionMatchStatus = (
        TransactionMatchStatus.UNMATCHED
    )
    flags: list[str] = Field(default_factory=list)

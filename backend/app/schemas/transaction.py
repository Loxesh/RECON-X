
from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.models.enums import (
    SourceType,
    TransactionDirection,
    TransactionValidity,
    TransactionMatchStatus,
)
from app.schemas.common import ApiSchema


class TransactionResponse(ApiSchema):
    """Canonical transaction information returned by the API."""

    id: str
    job_id: str
    file_id: str

    source_type: SourceType
    source_row: int = Field(ge=1)

    txn_ref: str | None = None
    reference_norm: str | None = None
    txn_date: datetime

    # Financial values are exposed as decimal strings.
    amount: str
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    direction: TransactionDirection

    description_raw: str | None = None
    description_norm: str | None = None
    fingerprint: str

    validity: TransactionValidity
    validation_errors: list[dict] = Field(default_factory=list)

    match_status: TransactionMatchStatus
    flags: list[str] = Field(default_factory=list)


class TransactionListFilters(ApiSchema):
    """Filters supported when listing transactions."""

    source_type: SourceType | None = None
    validity: TransactionValidity | None = None
    match_status: TransactionMatchStatus | None = None

    reference: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None


class TransactionAmountSummary(ApiSchema):
    """Transaction amount summary represented without float arithmetic."""

    currency: str
    total_amount: str
    transaction_count: int = Field(ge=0)

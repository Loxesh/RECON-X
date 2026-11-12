
from datetime import datetime, timezone
from typing import Annotated, Any

from bson import ObjectId
from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    PlainSerializer,
    WithJsonSchema,
)


def validate_object_id(value: Any) -> ObjectId:
    """Accept a BSON ObjectId or a valid ObjectId string."""

    if isinstance(value, ObjectId):
        return value

    if isinstance(value, str) and ObjectId.is_valid(value):
        return ObjectId(value)

    raise ValueError("Invalid MongoDB ObjectId")


PyObjectId = Annotated[
    ObjectId,
    BeforeValidator(validate_object_id),
    PlainSerializer(str, return_type=str, when_used="json"),
    WithJsonSchema({"type": "string", "pattern": "^[0-9a-fA-F]{24}$"}),
]


def utc_now() -> datetime:
    """Return the current timezone-aware UTC datetime."""

    return datetime.now(timezone.utc)


class DocumentBase(BaseModel):
    """Shared fields and validation for MongoDB documents."""

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        extra="forbid",
        validate_assignment=True,
    )

    id: PyObjectId = Field(
        default_factory=ObjectId,
        alias="_id",
    )

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    schema_version: int = Field(default=1, ge=1)


class TenantDocument(DocumentBase):
    """
    Base for tenant-owned collections.

    org_id is required and represents the owning organisation.
    """

    org_id: str = Field(min_length=1, max_length=100)

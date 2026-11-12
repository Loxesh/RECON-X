
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field


T = TypeVar("T")


class ApiSchema(BaseModel):
    """Shared configuration for API request and response schemas."""

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )


class ApiResponse(ApiSchema, Generic[T]):
    """Standard successful API response envelope."""

    success: bool = True
    message: str = "Request completed successfully"
    data: T | None = None


class PaginationParams(ApiSchema):
    """Pagination parameters for collection endpoints."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PaginationMetadata(ApiSchema):
    """Pagination details returned by collection endpoints."""

    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total_items: int = Field(ge=0)
    total_pages: int = Field(ge=0)


class PaginatedResponse(ApiSchema, Generic[T]):
    """Standard paginated API response."""

    success: bool = True
    message: str = "Records retrieved successfully"
    data: list[T]
    pagination: PaginationMetadata

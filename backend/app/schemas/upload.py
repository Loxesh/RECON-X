
from datetime import date, datetime

from pydantic import Field, field_validator

from app.models.enums import SourceType
from app.schemas.common import ApiSchema


class UploadPeriodSchema(ApiSchema):
    """Financial period covered by an uploaded file."""

    start_date: date
    end_date: date

    @field_validator("end_date")
    @classmethod
    def validate_end_date(cls, value, info):
        start_date = info.data.get("start_date")

        if start_date is not None and value < start_date:
            raise ValueError(
                "End date cannot be earlier than start date."
            )

        return value


class UploadMetadataSchema(ApiSchema):
    """Metadata supplied when initiating a financial file upload."""

    source_type: SourceType
    period: UploadPeriodSchema | None = None


class UploadedFileResponse(ApiSchema):
    """Safe uploaded-file information returned by the API."""

    id: str
    original_filename: str
    source_type: SourceType
    content_type: str
    size_bytes: int = Field(ge=1)
    sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
    scan_status: str
    created_at: datetime


class UploadInitiationResponse(ApiSchema):
    """Response returned after an upload is accepted."""

    upload_id: str
    file_id: str
    status: str
    message: str


from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.base import TenantDocument
from app.models.enums import SourceType


class FilePeriod(BaseModel):
    """Period covered by the uploaded financial file."""

    model_config = ConfigDict(extra="forbid")

    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_date_range(self):
        if self.start_date > self.end_date:
            raise ValueError("Period start_date cannot be after end_date")
        return self


class UploadedFileDocument(TenantDocument):
    source_type: SourceType
    original_filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=150)
    size_bytes: int = Field(gt=0)
    sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
    storage_bucket: str = Field(min_length=1)
    storage_key: str = Field(min_length=1)
    scan_status: str = "PENDING"
    uploaded_by: str = Field(min_length=1)
    period: FilePeriod | None = None

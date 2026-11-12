
from datetime import date

from pydantic import BaseModel, Field, model_validator

from app.models.base import TenantDocument
from app.models.enums import SourceType


class FilePeriod(BaseModel):
    """Period covered by an uploaded financial file."""

    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_period(self):
        if self.start_date > self.end_date:
            raise ValueError("Period start date cannot be after end date.")
        return self


class UploadedFileDocument(TenantDocument):
    source_type: SourceType
    original_filename: str = Field(min_length=1, max_length=255)
    content_type: str
    size_bytes: int = Field(gt=0)
    sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
    storage_bucket: str
    storage_key: str
    scan_status: str = "PENDING"
    uploaded_by: str
    period: FilePeriod | None = None

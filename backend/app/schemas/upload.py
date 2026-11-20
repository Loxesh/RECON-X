
from datetime import date, datetime

from pydantic import Field, field_validator

from app.models.enums import SourceType
from app.schemas.common import ApiSchema


class UploadPeriodSchema(ApiSchema):
    start_date: date
    end_date: date

    @field_validator("end_date")
    @classmethod
    def validate_end_date(cls, value, info):
        start_date = info.data.get("start_date")

        if start_date is not None and value < start_date:
            raise ValueError("End date cannot be earlier than start date.")

        return value


class UploadMetadataSchema(ApiSchema):
    source_type: SourceType
    period: UploadPeriodSchema | None = None


class UploadedFileResponse(ApiSchema):
    id: str
    ingestion_job_id: str
    ingestion_status: str
    original_filename: str
    source_type: SourceType
    content_type: str
    size_bytes: int = Field(ge=1)
    sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
    scan_status: str
    created_at: datetime


class IngestionJobStatusResponse(ApiSchema):
    file_id: str
    ingestion_job_id: str
    status: str
    counts: dict[str, int]
    errors_summary: list[str]
    attempts: int
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None

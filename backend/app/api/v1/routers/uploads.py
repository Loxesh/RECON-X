
"""Tenant-scoped secure upload and ingestion status API."""

import logging
from datetime import date, datetime, timezone
from hashlib import sha256

from bson import ObjectId
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Request,
    UploadFile,
    status,
)

from app.api.deps.auth_deps import require_permission
from app.core.config import settings
from app.core.permissions import Permission
from app.ingestion.file_validator import (
    FileValidationError,
    validate_uploaded_file,
)
from app.integrations.object_storage import create_object_storage
from app.models.enums import SourceType
from app.schemas.upload import (
    IngestionJobStatusResponse,
    UploadMetadataSchema,
    UploadPeriodSchema,
    UploadedFileResponse,
)
from app.services.upload_service import (
    UploadConflictError,
    UploadService,
)
from app.workers.tasks.ingest_task import process_ingestion

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/uploads", tags=["Uploads"])


@router.post(
    "",
    response_model=UploadedFileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a financial source file",
)
async def upload_file(
    request: Request,
    idempotency_key: str = Header(
        ...,
        alias="Idempotency-Key",
        min_length=1,
        max_length=128,
    ),
    source_type: SourceType = Form(...),
    period_start_date: date | None = Form(None),
    period_end_date: date | None = Form(None),
    file: UploadFile = File(...),
    current_user: dict = Depends(
        require_permission(Permission.UPLOADS_CREATE.value)
    ),
):
    """Validate, store, register and queue a financial source file."""

    org_id = current_user.get("org_id")
    if not isinstance(org_id, str) or not ObjectId.is_valid(org_id):
        raise HTTPException(
            status_code=403,
            detail="Valid organisation context is unavailable.",
        )

    database = getattr(request.app.state, "mongodb_database", None)
    if database is None:
        raise HTTPException(
            status_code=503,
            detail="Database is unavailable.",
        )

    if (period_start_date is None) != (period_end_date is None):
        raise HTTPException(
            status_code=422,
            detail="Both period start and end dates must be provided together.",
        )

    period = None
    if period_start_date is not None and period_end_date is not None:
        try:
            period = UploadPeriodSchema(
                start_date=period_start_date,
                end_date=period_end_date,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None

    metadata = UploadMetadataSchema(
        source_type=source_type,
        period=period,
    )

    try:
        content = await file.read(settings.max_upload_bytes + 1)
        validated = validate_uploaded_file(
            filename=file.filename,
            content_type=file.content_type,
            content=content,
            max_size_bytes=settings.max_upload_bytes,
        )
    except FileValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    finally:
        await file.close()

    now = datetime.now(timezone.utc)
    file_id = ObjectId()
    digest = sha256(validated.content).hexdigest()

    object_key = (
        f"{org_id}/{now.year:04d}/{now.month:02d}/{file_id}/original"
    )

    try:
        storage = create_object_storage()
        storage.put_object(
            key=object_key,
            content=validated.content,
            content_type=validated.content_type,
        )
    except Exception:
        logger.exception("Private file storage failed")
        raise HTTPException(
            status_code=500,
            detail="The uploaded file could not be stored.",
        ) from None

    file_document = {
        "_id": file_id,
        "source_type": metadata.source_type.value,
        "original_filename": validated.original_filename,
        "content_type": validated.content_type,
        "size_bytes": validated.size_bytes,
        "sha256": digest,
        "storage_bucket": (
            settings.s3_bucket
            if settings.object_storage_provider.lower() == "s3"
            else settings.upload_storage_bucket
        ),
        "storage_key": object_key,
        "scan_status": "PENDING",
        "uploaded_by": str(current_user.get("_id")),
        "period": (
            metadata.period.model_dump()
            if metadata.period is not None
            else None
        ),
        "created_at": now,
        "updated_at": now,
        "schema_version": 1,
    }

    upload_service = UploadService(database, org_id)

    try:
        saved_file, saved_job, created = (
            upload_service.create_upload_and_job(
                file_document=file_document,
                idempotency_key=idempotency_key,
            )
        )
    except UploadConflictError as exc:
        try:
            storage.delete_object(object_key)
        except Exception:
            logger.exception("Failed to clean up duplicate upload object")

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from None
    except Exception:
        logger.exception("Upload and ingestion job registration failed")
        try:
            storage.delete_object(object_key)
        except Exception:
            logger.exception("Failed to clean up stored object")
        raise HTTPException(
            status_code=500,
            detail="Upload registration failed.",
        ) from None

    # A repeated idempotency key reuses the original file and job.
    # Remove the newly staged object because it is not the registered file.
    if not created:
        try:
            storage.delete_object(object_key)
        except Exception:
            logger.exception("Failed to clean up repeated upload object")

    # Only a newly registered upload is sent to the worker.
    if created:
        try:
            process_ingestion.delay(
                org_id,
                str(saved_file["_id"]),
                str(saved_job["_id"]),
            )
        except Exception:
            logger.exception("Could not queue ingestion task")
            raise HTTPException(
                status_code=503,
                detail=(
                    "Upload was registered, but ingestion could not be "
                    "queued. The job remains pending."
                ),
            ) from None

    return UploadedFileResponse(
        id=str(saved_file["_id"]),
        ingestion_job_id=str(saved_job["_id"]),
        ingestion_status=saved_job["status"],
        original_filename=saved_file["original_filename"],
        source_type=SourceType(saved_file["source_type"]),
        content_type=saved_file["content_type"],
        size_bytes=saved_file["size_bytes"],
        sha256=saved_file["sha256"],
        scan_status=saved_file["scan_status"],
        created_at=saved_file["created_at"],
    )


@router.get(
    "/{file_id}/status",
    response_model=IngestionJobStatusResponse,
    summary="Get ingestion job status",
)
def get_upload_status(
    file_id: str,
    request: Request,
    current_user: dict = Depends(
        require_permission(Permission.UPLOADS_READ.value)
    ),
):
    """Return ingestion status for a file owned by the authenticated tenant."""

    org_id = current_user.get("org_id")
    if not isinstance(org_id, str) or not ObjectId.is_valid(org_id):
        raise HTTPException(
            status_code=403,
            detail="Valid organisation context is unavailable.",
        )

    if not ObjectId.is_valid(file_id):
        raise HTTPException(status_code=404, detail="Upload not found.")

    database = getattr(request.app.state, "mongodb_database", None)
    if database is None:
        raise HTTPException(
            status_code=503,
            detail="Database is unavailable.",
        )

    file_document = database["uploaded_files"].find_one(
        {
            "_id": ObjectId(file_id),
            "org_id": org_id,
        }
    )
    if file_document is None:
        raise HTTPException(status_code=404, detail="Upload not found.")

    job = database["ingestion_jobs"].find_one(
        {
            "org_id": org_id,
            "file_id": str(file_document["_id"]),
        }
    )
    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Ingestion job not found.",
        )

    return IngestionJobStatusResponse(
        file_id=str(file_document["_id"]),
        ingestion_job_id=str(job["_id"]),
        status=job["status"],
        counts=job.get(
            "counts",
            {"total": 0, "valid": 0, "invalid": 0},
        ),
        errors_summary=job.get("errors_summary", []),
        attempts=job.get("attempts", 0),
        created_at=job["created_at"],
        started_at=job.get("started_at"),
        finished_at=job.get("finished_at"),
    )

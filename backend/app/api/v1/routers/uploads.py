
"""Tenant-scoped secure financial file upload API."""

import logging
from datetime import date, datetime, timezone
from hashlib import sha256

from bson import ObjectId
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
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
from app.integrations.object_storage import LocalPrivateObjectStorage
from app.models.enums import SourceType
from app.repositories.tenant_collections import UploadedFileRepository
from app.schemas.upload import (
    UploadMetadataSchema,
    UploadPeriodSchema,
    UploadedFileResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/uploads",
    tags=["Uploads"],
)


@router.post(
    "",
    response_model=UploadedFileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a financial source file",
)
async def upload_file(
    request: Request,
    source_type: SourceType = Form(...),
    period_start_date: date | None = Form(None),
    period_end_date: date | None = Form(None),
    file: UploadFile = File(...),
    current_user: dict = Depends(
        require_permission(Permission.UPLOADS_CREATE.value)
    ),
):
    """Validate, privately store and register an uploaded source file."""

    org_id = current_user.get("org_id")

    if not isinstance(org_id, str) or not org_id.strip():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Valid organisation context is unavailable.",
        )

    database = getattr(request.app.state, "mongodb_database", None)

    if database is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable.",
        )

    if (period_start_date is None) != (period_end_date is None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
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
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from None

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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from None
    finally:
        await file.close()

    file_id = ObjectId()
    now = datetime.now(timezone.utc)
    digest = sha256(validated.content).hexdigest()

    object_key = (
        f"{org_id}/"
        f"{now.year:04d}/"
        f"{now.month:02d}/"
        f"{file_id}/original"
    )

    storage = LocalPrivateObjectStorage(
        settings.private_upload_storage_path
    )

    try:
        storage.put_object(
            key=object_key,
            content=validated.content,
            content_type=validated.content_type,
        )
    except Exception:
        logger.exception("Private file storage failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The uploaded file could not be stored.",
        ) from None

    document = {
        "_id": file_id,
        "org_id": org_id,
        "source_type": metadata.source_type.value,
        "original_filename": validated.original_filename,
        "content_type": validated.content_type,
        "size_bytes": validated.size_bytes,
        "sha256": digest,
        "storage_bucket": settings.upload_storage_bucket,
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

    try:
        repository = UploadedFileRepository(database, org_id)
        repository.create(document)
    except Exception:
        logger.exception("Upload metadata registration failed")

        try:
            storage.delete_object(object_key)
        except Exception:
            logger.exception("Failed to clean up stored file after database error")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Upload metadata could not be saved.",
        ) from None

    return UploadedFileResponse(
        id=str(file_id),
        original_filename=validated.original_filename,
        source_type=metadata.source_type,
        content_type=validated.content_type,
        size_bytes=validated.size_bytes,
        sha256=digest,
        scan_status="PENDING",
        created_at=now,
    )

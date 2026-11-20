
"""Background ingestion task for RECON X."""

import logging

from bson import ObjectId
from celery.exceptions import Reject
from pymongo import MongoClient

from app.core.config import settings
from app.ingestion.csv_xlsx_parser import parse_uploaded_file
from app.ingestion.header_mapper import map_headers
from app.ingestion.validators import validate_parsed_rows
from app.ingestion.normalizer import normalize_rows
from app.integrations.object_storage import create_object_storage
from app.models.enums import SourceType
from app.services.upload_service import UploadService
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _get_database():
    """Create a MongoDB connection for the worker."""

    if settings.mongodb_uri is None:
        raise RuntimeError("MongoDB URI is not configured.")

    client = MongoClient(
        settings.mongodb_uri.get_secret_value(),
        serverSelectionTimeoutMS=settings.mongodb_server_selection_timeout_ms,
        connectTimeoutMS=settings.mongodb_connect_timeout_ms,
        socketTimeoutMS=settings.mongodb_socket_timeout_ms,
    )

    return client, client[settings.mongodb_database]


@celery_app.task(
    bind=True,
    name="app.workers.tasks.ingest_task.process_ingestion",
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
)
def process_ingestion(
    self,
    org_id: str,
    file_id: str,
    job_id: str,
):
    """Parse, validate and normalize an uploaded financial file."""

    if not all(
        ObjectId.is_valid(value)
        for value in (org_id, file_id, job_id)
    ):
        raise Reject("Invalid ingestion identifiers.", requeue=False)

    client = None
    service = None
    claimed = False

    try:
        client, database = _get_database()
        service = UploadService(database, org_id)

        # Atomically claim the job to prevent duplicate execution.
        job = service.claim_job(job_id)

        if job is None:
            logger.info(
                "Ingestion job was already claimed or completed: %s",
                job_id,
            )
            return {"status": "SKIPPED", "job_id": job_id}

        claimed = True

        # Confirm that the supplied file belongs to this job.
        if job.get("file_id") != file_id:
            raise RuntimeError(
                "The supplied file ID does not match the ingestion job."
            )

        uploaded_file = database["uploaded_files"].find_one({
            "_id": ObjectId(file_id),
            "org_id": org_id,
        })

        if uploaded_file is None:
            raise RuntimeError("The uploaded file record was not found.")

        storage = create_object_storage()
        content = storage.get_object(uploaded_file["storage_key"])

        filename = uploaded_file["original_filename"]
        source_type = SourceType(uploaded_file["source_type"])

        parsed = parse_uploaded_file(filename, content)
        parse_error_count = len(parsed.issues)

        if not parsed.rows:
            counts = {
                "total": parse_error_count,
                "valid": 0,
                "invalid": parse_error_count,
            }

            service.update_job(
                job_id,
                status="COMPLETED",
                counts=counts,
                error=(
                    parsed.issues[0].message
                    if parsed.issues
                    else "No transaction rows found."
                ),
            )

            return {
                "status": "COMPLETED",
                "job_id": job_id,
                "counts": counts,
            }

        headers = list(parsed.rows[0].raw_row.keys())
        mapping = map_headers(headers, source_type)

        if not mapping.is_valid:
            messages = [
                issue.message for issue in mapping.issues
            ]

            total = len(parsed.rows) + parse_error_count
            counts = {
                "total": total,
                "valid": 0,
                "invalid": total,
            }

            service.update_job(
                job_id,
                status="COMPLETED",
                counts=counts,
                error="; ".join(messages[:5]),
            )

            return {
                "status": "COMPLETED",
                "job_id": job_id,
                "counts": counts,
            }

        validation = validate_parsed_rows(parsed.rows, mapping)
        normalization = normalize_rows(validation.rows)

        valid_count = sum(
            validated.is_valid and normalized.is_valid
            for validated, normalized in zip(
                validation.rows,
                normalization.rows,
            )
        )

        total_count = len(parsed.rows) + parse_error_count
        invalid_count = total_count - valid_count

        counts = {
            "total": total_count,
            "valid": valid_count,
            "invalid": invalid_count,
        }

        errors = []

        if parsed.issues:
            errors.extend(issue.message for issue in parsed.issues)

        for row in validation.rows:
            errors.extend(issue.message for issue in row.issues)

        for row in normalization.rows:
            errors.extend(issue.message for issue in row.issues)

        service.update_job(
            job_id,
            status="COMPLETED",
            counts=counts,
            error="; ".join(errors[:5]) if errors else None,
        )

        logger.info(
            "Ingestion completed: job=%s total=%s valid=%s invalid=%s",
            job_id,
            total_count,
            valid_count,
            invalid_count,
        )

        return {
            "status": "COMPLETED",
            "job_id": job_id,
            "counts": counts,
        }

    except Reject:
        raise

    except Exception as exc:
        logger.exception("Ingestion failed for job %s", job_id)

        if service is not None and claimed:
            try:
                service.update_job(
                    job_id,
                    status="FAILED",
                    error=str(exc)[:500],
                )
            except Exception:
                logger.exception(
                    "Could not update failed job status: %s",
                    job_id,
                )

        raise self.retry(exc=exc)

    finally:
        if client is not None:
            client.close()

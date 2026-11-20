
"""Tenant-scoped upload registration and ingestion job lifecycle."""

from datetime import date, datetime, time, timezone
from typing import Any

from bson import ObjectId
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError


class UploadConflictError(Exception):
    """An upload conflicts with an existing file or request."""


def _to_bson_compatible(value: Any) -> Any:
    """Convert Python date values into BSON-compatible UTC datetimes."""

    if isinstance(value, datetime):
        return value

    if isinstance(value, date):
        return datetime.combine(value, time.min, tzinfo=timezone.utc)

    if isinstance(value, dict):
        return {
            key: _to_bson_compatible(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [_to_bson_compatible(item) for item in value]

    if isinstance(value, tuple):
        return tuple(_to_bson_compatible(item) for item in value)

    return value


def _canonicalize_for_comparison(value: Any) -> Any:
    """Normalize dates and datetimes before comparing stored request data."""

    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)

        return value.astimezone(timezone.utc)

    if isinstance(value, date):
        return datetime.combine(value, time.min, tzinfo=timezone.utc)

    if isinstance(value, dict):
        return {
            key: _canonicalize_for_comparison(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [
            _canonicalize_for_comparison(item)
            for item in value
        ]

    return value


class UploadService:
    """Register uploaded files and their ingestion jobs."""

    def __init__(self, database, org_id: str):
        if not isinstance(org_id, str) or not ObjectId.is_valid(org_id):
            raise ValueError("A valid organisation ID is required.")

        self.database = database
        self.org_id = org_id

    def create_upload_and_job(
        self,
        *,
        file_document: dict[str, Any],
        idempotency_key: str,
    ) -> tuple[dict[str, Any], dict[str, Any], bool]:

        if (
            not isinstance(idempotency_key, str)
            or not idempotency_key.strip()
            or len(idempotency_key) > 128
        ):
            raise ValueError("A valid Idempotency-Key is required.")

        files = self.database["uploaded_files"]
        jobs = self.database["ingestion_jobs"]

        normalized_document = _to_bson_compatible(dict(file_document))

        def same_request(existing: dict[str, Any]) -> bool:
            return (
                existing.get("sha256") == normalized_document.get("sha256")
                and existing.get("source_type") == normalized_document.get("source_type")
                and _canonicalize_for_comparison(
                    existing.get("period")
                )
                == _canonicalize_for_comparison(
                    normalized_document.get("period")
                )
            )

        existing = files.find_one({
            "org_id": self.org_id,
            "idempotency_key": idempotency_key,
        })

        if existing:
            if not same_request(existing):
                raise UploadConflictError(
                    "This Idempotency-Key was already used for a different upload."
                )

            job = jobs.find_one({
                "org_id": self.org_id,
                "file_id": str(existing["_id"]),
            })

            if job is None:
                raise UploadConflictError(
                    "The existing upload has no ingestion job."
                )

            return existing, job, False

        duplicate = files.find_one({
            "org_id": self.org_id,
            "sha256": normalized_document["sha256"],
            "source_type": normalized_document["source_type"],
        })

        if duplicate:
            raise UploadConflictError(
                "This file has already been uploaded for this source."
            )

        now = datetime.now(timezone.utc)

        document = normalized_document
        document["org_id"] = self.org_id
        document["idempotency_key"] = idempotency_key
        document.setdefault("created_at", now)
        document.setdefault("updated_at", now)

        try:
            inserted = files.insert_one(document)

        except DuplicateKeyError:
            existing = files.find_one({
                "org_id": self.org_id,
                "idempotency_key": idempotency_key,
            })

            if existing and same_request(existing):
                job = jobs.find_one({
                    "org_id": self.org_id,
                    "file_id": str(existing["_id"]),
                })

                if job:
                    return existing, job, False

            raise UploadConflictError(
                "The file or idempotency key already exists."
            ) from None

        file_id = inserted.inserted_id

        job_document = {
            "org_id": self.org_id,
            "file_id": str(file_id),
            "status": "PENDING",
            "counts": {
                "total": 0,
                "valid": 0,
                "invalid": 0,
            },
            "errors_summary": [],
            "attempts": 0,
            "created_at": now,
            "updated_at": now,
            "started_at": None,
            "finished_at": None,
            "schema_version": 1,
        }

        try:
            job_inserted = jobs.insert_one(job_document)

        except Exception:
            files.delete_one({
                "_id": file_id,
                "org_id": self.org_id,
            })
            raise

        saved_file = files.find_one({
            "_id": file_id,
            "org_id": self.org_id,
        })

        saved_job = jobs.find_one({
            "_id": job_inserted.inserted_id,
            "org_id": self.org_id,
        })

        return saved_file, saved_job, True

    def claim_job(self, job_id: str) -> dict[str, Any] | None:
        """Atomically claim a pending or previously failed job."""

        if not ObjectId.is_valid(job_id):
            return None

        now = datetime.now(timezone.utc)

        return self.database["ingestion_jobs"].find_one_and_update(
            {
                "_id": ObjectId(job_id),
                "org_id": self.org_id,
                "status": {"$in": ["PENDING", "FAILED"]},
            },
            {
                "$set": {
                    "status": "PROCESSING",
                    "started_at": now,
                    "updated_at": now,
                },
                "$inc": {"attempts": 1},
            },
            return_document=ReturnDocument.AFTER,
        )

    def update_job(
        self,
        job_id: str,
        *,
        status: str,
        counts: dict[str, int] | None = None,
        error: str | None = None,
    ) -> bool:

        allowed = {"PENDING", "PROCESSING", "COMPLETED", "FAILED"}

        if status not in allowed:
            raise ValueError("Unsupported ingestion job status.")

        if not ObjectId.is_valid(job_id):
            return False

        now = datetime.now(timezone.utc)

        updates: dict[str, Any] = {
            "status": status,
            "updated_at": now,
        }

        if status == "PROCESSING":
            updates["started_at"] = now

        if status in {"COMPLETED", "FAILED"}:
            updates["finished_at"] = now

        if counts is not None:
            total = counts.get("total", 0)
            valid = counts.get("valid", 0)
            invalid = counts.get("invalid", 0)

            if (
                any(
                    isinstance(value, bool)
                    or not isinstance(value, int)
                    or value < 0
                    for value in (total, valid, invalid)
                )
                or valid + invalid > total
            ):
                raise ValueError("Invalid ingestion row counts.")

            updates["counts"] = {
                "total": total,
                "valid": valid,
                "invalid": invalid,
            }

        if error:
            updates["errors_summary"] = [error]

        result = self.database["ingestion_jobs"].update_one(
            {
                "_id": ObjectId(job_id),
                "org_id": self.org_id,
            },
            {"$set": updates},
        )

        return result.modified_count == 1

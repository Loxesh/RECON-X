
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO

import pytest
from bson import ObjectId
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import auth_deps
from app.api.v1.routers import uploads
from app.core.config import settings
from app.core.security import create_access_token
from app.services.upload_service import UploadConflictError


class FakeCollection:
    """Small in-memory collection for upload API tests."""

    def __init__(self):
        self.documents = []

    def find_one(self, query):
        for document in self.documents:
            if all(document.get(key) == value for key, value in query.items()):
                return document
        return None


class FakeDatabase:
    """In-memory database used by the test environment."""

    def __init__(self):
        self.collections = {
            "uploaded_files": FakeCollection(),
            "ingestion_jobs": FakeCollection(),
        }

    def __getitem__(self, collection_name):
        return self.collections[collection_name]


@pytest.fixture
def upload_test_environment(tmp_path, monkeypatch):
    """Create an isolated upload API environment."""

    org_id = str(ObjectId())
    user_id = ObjectId()

    user = {
        "_id": user_id,
        "org_id": org_id,
        "email": "upload-test@example.com",
        "roles": ["org_admin"],
        "status": "ACTIVE",
    }

    database = FakeDatabase()

    app = FastAPI()
    app.include_router(uploads.router, prefix="/api/v1")
    app.state.mongodb_database = database

    storage_path = tmp_path / "private_uploads"

    monkeypatch.setattr(
        settings,
        "private_upload_storage_path",
        str(storage_path),
    )
    monkeypatch.setattr(settings, "max_upload_bytes", 1024)
    monkeypatch.setattr(settings, "object_storage_provider", "local")

    monkeypatch.setattr(
        auth_deps,
        "get_active_user",
        lambda database, *, user_id, org_id: (
            user
            if user_id == str(user["_id"])
            and org_id == user["org_id"]
            else None
        ),
    )

    saved_files = []
    saved_jobs = []
    queued_tasks = []

    class FakeUploadService:
        def __init__(self, service_database, repository_org_id):
            assert service_database is database
            assert repository_org_id == org_id

            self.database = service_database
            self.org_id = repository_org_id

        def create_upload_and_job(
            self,
            *,
            file_document,
            idempotency_key,
        ):
            files_collection = self.database["uploaded_files"]
            jobs_collection = self.database["ingestion_jobs"]

            existing = files_collection.find_one(
                {
                    "org_id": self.org_id,
                    "idempotency_key": idempotency_key,
                }
            )

            if existing:
                same_payload = (
                    existing.get("sha256") == file_document.get("sha256")
                    and existing.get("source_type")
                    == file_document.get("source_type")
                    and existing.get("period") == file_document.get("period")
                )

                if not same_payload:
                    raise UploadConflictError(
                        "Idempotency key was already used for another request."
                    )

                existing_job = jobs_collection.find_one(
                    {
                        "org_id": self.org_id,
                        "file_id": str(existing["_id"]),
                    }
                )

                return existing, existing_job, False

            duplicate = files_collection.find_one(
                {
                    "org_id": self.org_id,
                    "sha256": file_document["sha256"],
                    "source_type": file_document["source_type"],
                }
            )

            if duplicate:
                raise UploadConflictError(
                    "This file has already been uploaded for this source."
                )

            now = datetime.now(timezone.utc)

            saved_file = dict(file_document)
            saved_file["_id"] = file_document.get("_id", ObjectId())
            saved_file["org_id"] = self.org_id
            saved_file["idempotency_key"] = idempotency_key
            saved_file.setdefault("created_at", now)
            saved_file.setdefault("updated_at", now)

            saved_job = {
                "_id": ObjectId(),
                "org_id": self.org_id,
                "file_id": str(saved_file["_id"]),
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

            # Save in the fake database so the status endpoint can find them.
            files_collection.documents.append(saved_file)
            jobs_collection.documents.append(saved_job)

            saved_files.append(saved_file)
            saved_jobs.append(saved_job)

            return saved_file, saved_job, True

    monkeypatch.setattr(
        uploads,
        "UploadService",
        FakeUploadService,
    )

    monkeypatch.setattr(
        uploads.process_ingestion,
        "delay",
        lambda org_id, file_id, job_id: queued_tasks.append(
            (org_id, file_id, job_id)
        ),
    )

    token = create_access_token(
        user_id=str(user_id),
        org_id=org_id,
        roles=user["roles"],
    )

    client = TestClient(app)

    return {
        "app": app,
        "client": client,
        "database": database,
        "org_id": org_id,
        "user": user,
        "token": token,
        "saved_files": saved_files,
        "saved_jobs": saved_jobs,
        "queued_tasks": queued_tasks,
    }


def auth_headers(environment, idempotency_key="test-upload-key"):
    return {
        "Authorization": f"Bearer {environment['token']}",
        "Idempotency-Key": idempotency_key,
    }


def valid_csv():
    return (
        b"Date,Amount,Description,Reference\n"
        b"2026-01-01,100.00,Test payment,REF001\n"
        b"2026-01-02,200.00,Second payment,REF002\n"
    )


def upload_csv(
    environment,
    *,
    idempotency_key="test-upload-key",
    content=None,
    filename="statement.csv",
):
    return environment["client"].post(
        "/api/v1/uploads",
        headers=auth_headers(environment, idempotency_key),
        data={"source_type": "BANK"},
        files={
            "file": (
                filename,
                content if content is not None else valid_csv(),
                "text/csv",
            )
        },
    )


def test_successful_upload_stores_file_and_creates_job(
    upload_test_environment,
):
    environment = upload_test_environment

    response = upload_csv(environment)

    assert response.status_code == 201

    body = response.json()

    assert body["id"]
    assert body["ingestion_job_id"]
    assert body["ingestion_status"] == "PENDING"
    assert body["original_filename"] == "statement.csv"

    assert len(environment["saved_files"]) == 1
    assert len(environment["saved_jobs"]) == 1
    assert len(environment["queued_tasks"]) == 1

    saved_file = environment["saved_files"][0]
    saved_job = environment["saved_jobs"][0]

    assert saved_file["org_id"] == environment["org_id"]
    assert saved_file["sha256"] == sha256(valid_csv()).hexdigest()
    assert saved_job["file_id"] == str(saved_file["_id"])
    assert saved_job["status"] == "PENDING"


def test_same_idempotency_request_does_not_create_duplicate_job(
    upload_test_environment,
):
    environment = upload_test_environment

    first_response = upload_csv(environment)
    second_response = upload_csv(environment)

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    assert first_response.json()["id"] == second_response.json()["id"]

    assert (
        first_response.json()["ingestion_job_id"]
        == second_response.json()["ingestion_job_id"]
    )

    assert len(environment["saved_files"]) == 1
    assert len(environment["saved_jobs"]) == 1
    assert len(environment["queued_tasks"]) == 1


def test_reusing_idempotency_key_with_different_file_returns_conflict(
    upload_test_environment,
):
    environment = upload_test_environment

    first_response = upload_csv(environment)

    changed_content = (
        b"Date,Amount,Description,Reference\n"
        b"2026-01-01,999.00,Different payment,REF999\n"
    )

    second_response = upload_csv(
        environment,
        content=changed_content,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409

    assert len(environment["saved_files"]) == 1
    assert len(environment["saved_jobs"]) == 1
    assert len(environment["queued_tasks"]) == 1


def test_duplicate_file_with_different_key_returns_conflict(
    upload_test_environment,
):
    environment = upload_test_environment

    first_response = upload_csv(
        environment,
        idempotency_key="first-request",
    )

    second_response = upload_csv(
        environment,
        idempotency_key="second-request",
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409

    assert len(environment["saved_files"]) == 1
    assert len(environment["saved_jobs"]) == 1
    assert len(environment["queued_tasks"]) == 1


def test_upload_status_is_observable(upload_test_environment):
    environment = upload_test_environment

    upload_response = upload_csv(environment)

    assert upload_response.status_code == 201

    file_id = upload_response.json()["id"]

    job = environment["saved_jobs"][0]
    job["status"] = "COMPLETED"
    job["counts"] = {
        "total": 10,
        "valid": 8,
        "invalid": 2,
    }
    job["attempts"] = 1

    response = environment["client"].get(
        f"/api/v1/uploads/{file_id}/status",
        headers=auth_headers(environment),
    )

    assert response.status_code == 200

    body = response.json()

    assert body["file_id"] == file_id
    assert body["ingestion_job_id"] == str(job["_id"])
    assert body["status"] == "COMPLETED"
    assert body["counts"]["total"] == 10
    assert body["counts"]["valid"] == 8
    assert body["counts"]["invalid"] == 2
    assert body["attempts"] == 1


def test_upload_status_does_not_expose_another_tenant_file(
    upload_test_environment,
):
    environment = upload_test_environment

    response = environment["client"].get(
        f"/api/v1/uploads/{ObjectId()}/status",
        headers=auth_headers(environment),
    )

    assert response.status_code == 404


def test_upload_rejects_unsupported_file_type(upload_test_environment):
    environment = upload_test_environment

    response = environment["client"].post(
        "/api/v1/uploads",
        headers=auth_headers(environment),
        data={"source_type": "BANK"},
        files={
            "file": (
                "document.txt",
                b"not a supported financial file",
                "text/plain",
            )
        },
    )

    assert response.status_code == 400
    assert environment["saved_files"] == []
    assert environment["saved_jobs"] == []
    assert environment["queued_tasks"] == []


def test_upload_rejects_oversized_file(upload_test_environment):
    environment = upload_test_environment

    oversized_content = (
        b"date,amount\n"
        + b"2026-01-01,100.00\n" * 100
    )

    response = environment["client"].post(
        "/api/v1/uploads",
        headers=auth_headers(environment),
        data={"source_type": "BANK"},
        files={
            "file": (
                "large.csv",
                oversized_content,
                "text/csv",
            )
        },
    )

    assert response.status_code == 400
    assert environment["saved_files"] == []
    assert environment["saved_jobs"] == []
    assert environment["queued_tasks"] == []


def test_upload_rejects_missing_authentication(upload_test_environment):
    environment = upload_test_environment

    response = environment["client"].post(
        "/api/v1/uploads",
        data={"source_type": "BANK"},
        files={
            "file": (
                "statement.csv",
                valid_csv(),
                "text/csv",
            )
        },
    )

    assert response.status_code == 401
    assert environment["saved_files"] == []
    assert environment["saved_jobs"] == []


def test_upload_rejects_user_without_upload_permission(
    upload_test_environment,
    monkeypatch,
):
    environment = upload_test_environment

    auditor = {
        **environment["user"],
        "roles": ["auditor"],
    }

    monkeypatch.setattr(
        auth_deps,
        "get_active_user",
        lambda database, *, user_id, org_id: (
            auditor
            if user_id == str(auditor["_id"])
            and org_id == auditor["org_id"]
            else None
        ),
    )

    auditor_token = create_access_token(
        user_id=str(auditor["_id"]),
        org_id=auditor["org_id"],
        roles=auditor["roles"],
    )

    response = environment["client"].post(
        "/api/v1/uploads",
        headers={
            "Authorization": f"Bearer {auditor_token}",
            "Idempotency-Key": "auditor-request",
        },
        data={"source_type": "BANK"},
        files={
            "file": (
                "statement.csv",
                valid_csv(),
                "text/csv",
            )
        },
    )

    assert response.status_code == 403
    assert environment["saved_files"] == []
    assert environment["saved_jobs"] == []
    assert environment["queued_tasks"] == []


def test_upload_returns_service_unavailable_without_database(
    upload_test_environment,
):
    environment = upload_test_environment
    environment["app"].state.mongodb_database = None

    response = environment["client"].post(
        "/api/v1/uploads",
        headers=auth_headers(environment),
        data={"source_type": "BANK"},
        files={
            "file": (
                "statement.csv",
                valid_csv(),
                "text/csv",
            )
        },
    )

    assert response.status_code == 503
    assert environment["saved_files"] == []
    assert environment["saved_jobs"] == []
    assert environment["queued_tasks"] == []

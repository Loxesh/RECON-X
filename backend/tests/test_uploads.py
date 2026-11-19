
from hashlib import sha256
from pathlib import Path

import pytest
from bson import ObjectId
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import auth_deps
from app.api.v1.routers import uploads
from app.core.config import settings
from app.core.security import create_access_token


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

    database = object()

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

    saved_documents = []

    class FakeUploadedFileRepository:
        def __init__(self, database, repository_org_id):
            assert database is app.state.mongodb_database
            assert repository_org_id == org_id

        def create(self, document):
            saved_documents.append(document)
            return document

    monkeypatch.setattr(
        uploads,
        "UploadedFileRepository",
        FakeUploadedFileRepository,
    )

    token = create_access_token(
        user_id=str(user_id),
        org_id=org_id,
        roles=user["roles"],
    )

    client = TestClient(app)

    return {
        "client": client,
        "app": app,
        "user": user,
        "token": token,
        "storage_path": storage_path,
        "saved_documents": saved_documents,
    }


def auth_headers(environment):
    return {
        "Authorization": f"Bearer {environment['token']}"
    }


def valid_csv():
    return b"date,amount\n2026-01-01,100.00\n"


def test_successful_upload_stores_file_and_metadata(
    upload_test_environment,
):
    environment = upload_test_environment
    content = valid_csv()

    response = environment["client"].post(
        "/api/v1/uploads",
        headers=auth_headers(environment),
        data={"source_type": "BANK"},
        files={
            "file": (
                "statement.csv",
                content,
                "text/csv",
            )
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["original_filename"] == "statement.csv"
    assert body["source_type"] == "BANK"
    assert body["size_bytes"] == len(content)
    assert body["sha256"] == sha256(content).hexdigest()
    assert body["scan_status"] == "PENDING"

    assert len(environment["saved_documents"]) == 1

    document = environment["saved_documents"][0]

    # Tenant identity must come from the authenticated user.
    assert document["org_id"] == environment["user"]["org_id"]
    assert document["uploaded_by"] == str(environment["user"]["_id"])

    # Verify the expected private object-key structure.
    assert document["storage_key"].startswith(
        f"{environment['user']['org_id']}/"
    )
    assert document["storage_key"].endswith("/original")

    # Verify that the original file exists in private storage.
    stored_file = (
        environment["storage_path"]
        / document["storage_key"]
    )

    assert stored_file.is_file()
    assert stored_file.read_bytes() == content

    # The response must not expose internal storage details.
    assert "storage_key" not in body
    assert "storage_bucket" not in body


def test_upload_rejects_unsupported_file_type(
    upload_test_environment,
):
    environment = upload_test_environment

    response = environment["client"].post(
        "/api/v1/uploads",
        headers=auth_headers(environment),
        data={"source_type": "BANK"},
        files={
            "file": (
                "malicious.txt",
                b"not a supported financial file",
                "text/plain",
            )
        },
    )

    assert response.status_code == 400
    assert environment["saved_documents"] == []


def test_upload_rejects_oversized_file(
    upload_test_environment,
):
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
    assert environment["saved_documents"] == []


def test_upload_rejects_missing_authentication(
    upload_test_environment,
):
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
    assert environment["saved_documents"] == []


def test_upload_rejects_user_without_upload_permission(
    upload_test_environment,
    monkeypatch,
):
    environment = upload_test_environment

    # Replace the authenticated user's role with auditor.
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
            "Authorization": f"Bearer {auditor_token}"
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
    assert environment["saved_documents"] == []


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
    assert environment["saved_documents"] == []

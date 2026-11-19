
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from app.integrations.object_storage import (
    LocalPrivateObjectStorage,
    S3ObjectStorage,
)


# --------------------------------------------------
# LOCAL STORAGE TESTS
# --------------------------------------------------

def test_object_is_stored_inside_private_directory(tmp_path):
    storage = LocalPrivateObjectStorage(tmp_path)

    storage.put_object(
        key="ORG001/2026/11/file123/original",
        content=b"private financial data",
        content_type="text/csv",
    )

    stored_file = (
        tmp_path
        / "ORG001"
        / "2026"
        / "11"
        / "file123"
        / "original"
    )

    assert stored_file.exists()
    assert stored_file.read_bytes() == b"private financial data"


def test_object_can_be_deleted(tmp_path):
    storage = LocalPrivateObjectStorage(tmp_path)
    key = "ORG001/2026/11/file123/original"

    storage.put_object(
        key=key,
        content=b"sample",
        content_type="text/csv",
    )

    storage.delete_object(key)

    assert not (
        tmp_path
        / "ORG001"
        / "2026"
        / "11"
        / "file123"
        / "original"
    ).exists()


@pytest.mark.parametrize(
    "key",
    [
        "../outside.txt",
        "/outside.txt",
        r"ORG001\..\outside.txt",
        "",
    ],
)
def test_path_traversal_keys_are_rejected(tmp_path, key):
    storage = LocalPrivateObjectStorage(tmp_path)

    with pytest.raises(ValueError):
        storage.put_object(
            key=key,
            content=b"data",
            content_type="text/plain",
        )


def test_existing_object_is_not_overwritten(tmp_path):
    storage = LocalPrivateObjectStorage(tmp_path)
    key = "ORG001/2026/11/file123/original"

    storage.put_object(key, b"original", "text/csv")

    with pytest.raises(FileExistsError):
        storage.put_object(key, b"replacement", "text/csv")

    stored_file = (
        tmp_path
        / "ORG001"
        / "2026"
        / "11"
        / "file123"
        / "original"
    )

    assert stored_file.read_bytes() == b"original"


def test_local_object_can_be_read(tmp_path):
    storage = LocalPrivateObjectStorage(tmp_path)
    key = "ORG001/2026/11/file123/original"

    storage.put_object(key, b"sample data", "text/csv")

    assert storage.get_object(key) == b"sample data"


def test_local_head_returns_metadata(tmp_path):
    storage = LocalPrivateObjectStorage(tmp_path)
    key = "ORG001/2026/11/file123/original"

    storage.put_object(key, b"sample", "text/csv")

    metadata = storage.head_object(key)

    assert metadata is not None
    assert metadata["ContentLength"] == 6


def test_local_head_returns_none_for_missing_object(tmp_path):
    storage = LocalPrivateObjectStorage(tmp_path)

    assert storage.head_object("missing/file.txt") is None


# --------------------------------------------------
# S3 STORAGE TESTS
# --------------------------------------------------

@pytest.fixture
def s3_storage():
    with patch(
        "app.integrations.object_storage.boto3.client"
    ) as mock_client:
        client = MagicMock()
        mock_client.return_value = client

        storage = S3ObjectStorage(
            endpoint_url="http://localhost:9000",
            bucket="recon-x-private-dev",
            region="us-east-1",
            access_key_id="test-access-key",
            secret_access_key="test-secret-key",
        )

        yield storage, client


def test_s3_upload_uses_private_bucket_and_immutable_key(s3_storage):
    storage, client = s3_storage
    key = "ORG001/2026/11/file123/original"

    storage.put_object(
        key=key,
        content=b"financial data",
        content_type="text/csv",
    )

    client.put_object.assert_called_once_with(
        Bucket="recon-x-private-dev",
        Key=key,
        Body=b"financial data",
        ContentType="text/csv",
        IfNoneMatch="*",
    )


def test_s3_download_returns_object_bytes(s3_storage):
    storage, client = s3_storage

    body = MagicMock()
    body.read.return_value = b"financial data"

    client.get_object.return_value = {"Body": body}

    result = storage.get_object("ORG001/2026/file123/original")

    assert result == b"financial data"


def test_s3_delete_removes_object(s3_storage):
    storage, client = s3_storage
    key = "ORG001/2026/file123/original"

    storage.delete_object(key)

    client.delete_object.assert_called_once_with(
        Bucket="recon-x-private-dev",
        Key=key,
    )


def test_s3_head_returns_object_metadata(s3_storage):
    storage, client = s3_storage

    client.head_object.return_value = {
        "ContentLength": 25,
        "ContentType": "text/csv",
        "ETag": '"abc123"',
    }

    result = storage.head_object("ORG001/2026/file123/original")

    assert result["ContentLength"] == 25
    assert result["ContentType"] == "text/csv"


def test_s3_head_returns_none_when_object_is_missing(s3_storage):
    storage, client = s3_storage

    client.head_object.side_effect = ClientError(
        {
            "Error": {
                "Code": "404",
                "Message": "Not Found",
            }
        },
        "HeadObject",
    )

    result = storage.head_object("ORG001/missing/original")

    assert result is None


def test_s3_generates_presigned_download_url(s3_storage):
    storage, client = s3_storage
    client.generate_presigned_url.return_value = (
        "http://localhost:9000/presigned-download"
    )

    result = storage.generate_presigned_download_url(
        "ORG001/2026/file123/original",
        expires_in=120,
    )

    assert result == "http://localhost:9000/presigned-download"

    client.generate_presigned_url.assert_called_once_with(
        ClientMethod="get_object",
        Params={
            "Bucket": "recon-x-private-dev",
            "Key": "ORG001/2026/file123/original",
        },
        ExpiresIn=120,
    )


def test_s3_rejects_invalid_storage_keys(s3_storage):
    storage, client = s3_storage

    with pytest.raises(ValueError):
        storage.put_object(
            key="../outside.txt",
            content=b"data",
            content_type="text/plain",
        )

    client.put_object.assert_not_called()


def test_s3_rejects_invalid_presigned_url_expiry(s3_storage):
    storage, client = s3_storage

    with pytest.raises(ValueError):
        storage.generate_presigned_download_url(
            "ORG001/file.txt",
            expires_in=5000,
        )

    client.generate_presigned_url.assert_not_called()

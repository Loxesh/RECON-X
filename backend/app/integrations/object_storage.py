
"""Provider-independent private object storage adapters."""

from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlparse
import os

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings


class ObjectStorage(Protocol):
    """Provider-independent object storage contract."""

    def put_object(
        self,
        key: str,
        content: bytes,
        content_type: str,
    ) -> None:
        ...

    def get_object(self, key: str) -> bytes:
        ...

    def delete_object(self, key: str) -> None:
        ...

    def head_object(self, key: str) -> dict[str, Any] | None:
        ...

    def generate_presigned_download_url(
        self,
        key: str,
        expires_in: int | None = None,
    ) -> str:
        ...


class LocalPrivateObjectStorage:
    """Private filesystem storage for local development."""

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve_key(self, key: str) -> Path:
        """Resolve a key without allowing path traversal."""

        if not key or "\\" in key or key.startswith("/"):
            raise ValueError("Invalid storage key.")

        parts = key.split("/")

        if any(part in {"", ".", ".."} for part in parts):
            raise ValueError("Invalid storage key.")

        destination = (self.root / Path(*parts)).resolve()

        if not destination.is_relative_to(self.root):
            raise ValueError("Storage key escapes the private storage root.")

        return destination

    def put_object(
        self,
        key: str,
        content: bytes,
        content_type: str,
    ) -> None:
        """Store an original file without exposing a public URL."""

        destination = self._resolve_key(key)
        destination.parent.mkdir(parents=True, exist_ok=True)

        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        descriptor = os.open(str(destination), flags, 0o600)

        try:
            with os.fdopen(descriptor, "wb") as file:
                file.write(content)
        except Exception:
            destination.unlink(missing_ok=True)
            raise

    def get_object(self, key: str) -> bytes:
        return self._resolve_key(key).read_bytes()

    def delete_object(self, key: str) -> None:
        """Remove a stored object during failed upload cleanup."""

        self._resolve_key(key).unlink(missing_ok=True)

    def head_object(self, key: str) -> dict[str, Any] | None:
        path = self._resolve_key(key)

        if not path.is_file():
            return None

        return {
            "ContentLength": path.stat().st_size,
            "ContentType": "application/octet-stream",
        }

    def generate_presigned_download_url(
        self,
        key: str,
        expires_in: int | None = None,
    ) -> str:
        raise NotImplementedError(
            "Local filesystem storage does not provide download URLs."
        )


class S3ObjectStorage:
    """Private S3-compatible storage adapter for MinIO and AWS S3."""

    def __init__(
        self,
        endpoint_url: str | None,
        bucket: str,
        region: str,
        access_key_id: str,
        secret_access_key: str,
    ):
        self.bucket = bucket

        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name=region,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
        )

    @staticmethod
    def _validate_key(key: str) -> None:
        if (
            not key
            or key.startswith("/")
            or "\\" in key
            or any(part in {"", ".", ".."} for part in key.split("/"))
        ):
            raise ValueError("Invalid storage key.")

    def put_object(
        self,
        key: str,
        content: bytes,
        content_type: str,
    ) -> None:
        self._validate_key(key)

        # Conditional creation prevents replacing an existing original.
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
            IfNoneMatch="*",
        )

    def get_object(self, key: str) -> bytes:
        self._validate_key(key)

        response = self.client.get_object(
            Bucket=self.bucket,
            Key=key,
        )

        return response["Body"].read()

    def delete_object(self, key: str) -> None:
        self._validate_key(key)

        self.client.delete_object(
            Bucket=self.bucket,
            Key=key,
        )

    def head_object(self, key: str) -> dict[str, Any] | None:
        self._validate_key(key)

        try:
            response = self.client.head_object(
                Bucket=self.bucket,
                Key=key,
            )
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")

            if code in {"404", "NoSuchKey", "NotFound"}:
                return None

            raise

        return {
            "ContentLength": response.get("ContentLength", 0),
            "ContentType": response.get("ContentType"),
            "ETag": response.get("ETag"),
            "LastModified": response.get("LastModified"),
        }

    def generate_presigned_download_url(
        self,
        key: str,
        expires_in: int | None = None,
    ) -> str:
        self._validate_key(key)

        expiry = (
            expires_in
            if expires_in is not None
            else settings.s3_presigned_url_expiry_seconds
        )

        if not 1 <= expiry <= 3600:
            raise ValueError("Presigned URL expiry must be 1–3600 seconds.")

        return self.client.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": self.bucket,
                "Key": key,
            },
            ExpiresIn=expiry,
        )


def create_object_storage() -> ObjectStorage:
    """Build the configured storage provider."""

    provider = settings.object_storage_provider.lower()

    if provider == "local":
        return LocalPrivateObjectStorage(
            settings.private_upload_storage_path
        )

    if provider == "s3":
        if not settings.s3_access_key_id:
            raise ValueError("S3_ACCESS_KEY_ID is required.")

        if settings.s3_secret_access_key is None:
            raise ValueError("S3_SECRET_ACCESS_KEY is required.")

        if not settings.s3_bucket:
            raise ValueError("S3_BUCKET is required.")

        if settings.s3_endpoint_url:
            parsed = urlparse(settings.s3_endpoint_url)

            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("S3_ENDPOINT_URL must be a valid HTTP(S) URL.")

        return S3ObjectStorage(
            endpoint_url=settings.s3_endpoint_url,
            bucket=settings.s3_bucket,
            region=settings.s3_region,
            access_key_id=settings.s3_access_key_id,
            secret_access_key=(
                settings.s3_secret_access_key.get_secret_value()
            ),
        )

    raise ValueError(
        f"Unsupported object storage provider: {provider}"
    )

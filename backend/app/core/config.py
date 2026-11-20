
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Central configuration for the RECON X backend."""

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "RECON X API"
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"

    # Runtime
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    redis_url: str = "redis://localhost:6379/0"

    secret_key: SecretStr = SecretStr(
        "replace-with-a-local-development-placeholder"
    )

    # JWT authentication
    jwt_secret_key: SecretStr | None = None
    jwt_issuer: str = "recon-x-local"
    jwt_audience: str = "recon-x-api"
    jwt_access_token_expire_minutes: int = Field(
        default=15,
        gt=0,
        le=60,
    )

    # MongoDB
    mongodb_uri: SecretStr | None = None
    mongodb_database: str = "RECON_X_DEV"
    mongodb_server_selection_timeout_ms: int = 5000
    mongodb_connect_timeout_ms: int = 5000
    mongodb_socket_timeout_ms: int = 10000
    mongodb_max_pool_size: int = 20

    # Upload security
    max_upload_bytes: int = Field(default=10 * 1024 * 1024, gt=0)
    private_upload_storage_path: str = str(
        BACKEND_DIR / "private_uploads"
    )
    upload_storage_bucket: str = "recon-x-private-dev"

    # Object storage
    object_storage_provider: str = "local"
    s3_endpoint_url: str | None = None
    s3_bucket: str = "recon-x-private-dev"
    s3_region: str = "us-east-1"
    s3_access_key_id: str | None = None
    s3_secret_access_key: SecretStr | None = None
    s3_presigned_url_expiry_seconds: int = Field(
        default=300,
        gt=0,
        le=3600,
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]


settings = Settings()


from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """
    Central configuration for the RECON X backend.

    Values are loaded from backend/.env and can also
    be overridden by environment variables.
    """

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

    # Security
    secret_key: SecretStr = SecretStr(
        "replace-with-a-local-development-placeholder"
    )

    # MongoDB
    mongodb_uri: SecretStr | None = None
    mongodb_database: str = "RECON_X_DEV"
    mongodb_server_selection_timeout_ms: int = 5000
    mongodb_connect_timeout_ms: int = 5000
    mongodb_socket_timeout_ms: int = 10000
    mongodb_max_pool_size: int = 20


settings = Settings()

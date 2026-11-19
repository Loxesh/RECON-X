
"""Password hashing and JWT security utilities for RECON X."""

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import (
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)

from app.core.config import settings


ALGORITHM = "HS256"

password_hasher = PasswordHasher()


def _get_jwt_secret() -> str:
    """Return the configured JWT signing secret."""

    if settings.jwt_secret_key is None:
        raise RuntimeError("JWT signing secret is not configured.")

    secret = settings.jwt_secret_key.get_secret_value()

    if len(secret) < 32:
        raise RuntimeError("JWT signing secret is too short.")

    return secret


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2."""

    if not isinstance(password, str) or not password:
        raise ValueError("Password must not be empty.")

    return password_hasher.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """Verify a password against its Argon2 hash."""

    if not isinstance(plain_password, str):
        return False

    if not isinstance(hashed_password, str) or not hashed_password:
        return False

    try:
        return password_hasher.verify(
            hashed_password,
            plain_password,
        )
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def create_access_token(
    *,
    user_id: str,
    org_id: str,
    roles: list[str],
) -> str:
    """Create a signed development access token."""

    if not user_id or not org_id:
        raise ValueError("User ID and organisation ID are required.")

    if not isinstance(roles, list) or not all(
        isinstance(role, str) and role.strip()
        for role in roles
    ):
        raise ValueError("Roles must be a list of non-empty strings.")

    now = datetime.now(timezone.utc)

    expires_at = now + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )

    payload = {
        "sub": user_id,
        "org_id": org_id,
        "roles": roles,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": now,
        "nbf": now,
        "exp": expires_at,
        "jti": str(uuid4()),
    }

    return jwt.encode(
        payload,
        _get_jwt_secret(),
        algorithm=ALGORITHM,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """Verify and decode a development access token."""

    if not isinstance(token, str) or not token.strip():
        raise jwt.InvalidTokenError("Token is missing.")

    return jwt.decode(
        token,
        _get_jwt_secret(),
        algorithms=[ALGORITHM],
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        options={
            "require": [
                "sub",
                "org_id",
                "roles",
                "iss",
                "aud",
                "iat",
                "nbf",
                "exp",
                "jti",
            ],
        },
    )

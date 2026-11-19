
"""Authentication dependencies for protected API routes."""

import jwt

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.security import _get_jwt_secret
from app.services.auth_service import get_active_user


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
) -> dict:
    """Verify the bearer token and return the active database user."""

    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise unauthorized

    database = getattr(request.app.state, "mongodb_database", None)

    if database is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable.",
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            key=_get_jwt_secret(),
            algorithms=["HS256"],
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

        user_id = payload.get("sub")
        org_id = payload.get("org_id")

        if not isinstance(user_id, str) or not isinstance(org_id, str):
            raise unauthorized

    except (jwt.PyJWTError, RuntimeError):
        raise unauthorized from None

    user = get_active_user(
        database,
        user_id=user_id,
        org_id=org_id,
    )

    if user is None:
        raise unauthorized

    return user

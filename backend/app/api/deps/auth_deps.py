
"""Authentication and permission dependencies for protected routes."""

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.permissions import has_permission
from app.core.security import decode_access_token
from app.services.auth_service import get_active_user


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
) -> dict:
    """Verify the JWT and retrieve the active database user."""

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
        payload = decode_access_token(credentials.credentials)

        user_id = payload.get("sub")
        org_id = payload.get("org_id")

        if not isinstance(user_id, str) or not isinstance(org_id, str):
            raise unauthorized

    except Exception:
        raise unauthorized from None

    user = get_active_user(
        database,
        user_id=user_id,
        org_id=org_id,
    )

    if user is None:
        raise unauthorized

    return user


def require_permission(permission: str):
    """Create a dependency that enforces a specific permission."""

    def permission_dependency(
        current_user: dict = Depends(get_current_user),
    ) -> dict:
        roles = current_user.get("roles", [])

        if not has_permission(roles, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )

        return current_user

    return permission_dependency

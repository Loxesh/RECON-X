
"""Authentication routes for RECON X."""

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps.auth_deps import get_current_user
from app.schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    TokenResponse,
)
from app.services.auth_service import (
    AuthenticationError,
    authenticate_user,
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate a user",
)
def login(
    credentials: LoginRequest,
    request: Request,
) -> TokenResponse:
    """Authenticate a user and return a JWT access token."""

    database = getattr(request.app.state, "mongodb_database", None)

    if database is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable.",
        )

    try:
        result = authenticate_user(
            database,
            organization_slug=credentials.organization_slug,
            email=str(credentials.email),
            password=credentials.password.get_secret_value(),
        )
        return TokenResponse(**result)

    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid organisation or credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


@router.get(
    "/me",
    response_model=CurrentUserResponse,
    response_model_by_alias=False,
    summary="Get the authenticated user",
)
def get_me(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Return the profile of the authenticated user."""

    return {
        **current_user,
        "_id": str(current_user["_id"]),
    }

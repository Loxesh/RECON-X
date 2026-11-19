
"""Pydantic schemas for authentication endpoints."""

from pydantic import BaseModel, EmailStr, Field, SecretStr, ConfigDict


class LoginRequest(BaseModel):
    """Credentials supplied by a user during login."""

    organization_slug: str = Field(
        min_length=2,
        max_length=100,
        pattern=r"^[a-z0-9-]+$",
    )
    email: EmailStr
    password: SecretStr


class TokenResponse(BaseModel):
    """JWT access-token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class CurrentUserResponse(BaseModel):
    """Authenticated user's public profile."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(alias="_id")
    org_id: str
    email: EmailStr
    roles: list[str]
    status: str

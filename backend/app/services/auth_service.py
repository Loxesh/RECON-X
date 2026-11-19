
"""Authentication service for RECON X."""

from typing import Any

from bson import ObjectId
from pymongo.database import Database

from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.repositories.organization import OrganizationRepository


class AuthenticationError(Exception):
    """Raised when user authentication fails."""


def authenticate_user(
    database: Database,
    *,
    organization_slug: str,
    email: str,
    password: str,
) -> dict[str, Any]:
    """
    Authenticate a user within a specific organisation.

    Organisation and user status are checked before issuing
    an access token. The organisation ID is obtained from
    MongoDB, never from client-supplied data.
    """

    organization_repository = OrganizationRepository(database)

    organization = organization_repository.get_by_slug(
        organization_slug
    )

    if not organization or organization.get("status") != "ACTIVE":
        raise AuthenticationError("Invalid organisation or credentials.")

    organization_id = str(organization["_id"])

    user = database["users"].find_one(
        {
            "org_id": organization_id,
            "email": email,
        }
    )

    if not user:
        raise AuthenticationError("Invalid organisation or credentials.")

    if user.get("status") != "ACTIVE":
        raise AuthenticationError("Invalid organisation or credentials.")

    password_hash = user.get("password_hash")

    if not password_hash or not verify_password(password, password_hash):
        raise AuthenticationError("Invalid organisation or credentials.")

    user_id = str(user["_id"])
    roles = user.get("roles", [])

    if not isinstance(roles, list) or not all(
        isinstance(role, str) and role.strip()
        for role in roles
    ):
        raise AuthenticationError("Invalid organisation or credentials.")

    access_token = create_access_token(
        user_id=user_id,
        org_id=organization_id,
        roles=roles,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.jwt_access_token_expire_minutes * 60,
    }


def get_active_user(
    database: Database,
    *,
    user_id: str,
    org_id: str,
) -> dict[str, Any] | None:
    """
    Retrieve an active user using verified JWT identity claims.

    Both organisation ID and user ID are required in the query.
    """

    if not ObjectId.is_valid(user_id):
        return None

    if not ObjectId.is_valid(org_id):
        return None

    user = database["users"].find_one(
        {
            "_id": ObjectId(user_id),
            "org_id": org_id,
            "status": "ACTIVE",
        }
    )

    return user


"""Trusted tenant-context dependencies."""

from fastapi import Depends, HTTPException, status

from app.api.deps.auth_deps import get_current_user


def get_current_org_id(
    current_user: dict = Depends(get_current_user),
) -> str:
    """Return the organisation ID belonging to the authenticated user."""

    org_id = current_user.get("org_id")

    if not isinstance(org_id, str) or not org_id.strip():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Valid organisation context is unavailable.",
        )

    return org_id


"""Tests for RECON X role permissions and tenant context."""

import pytest

from bson import ObjectId
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.deps.auth_deps import require_permission
from app.api.deps.tenant_deps import get_current_org_id
from app.core.permissions import (
    Permission,
    Role,
    ROLE_PERMISSIONS,
    has_permission,
)


def test_all_three_roles_are_defined():
    assert set(ROLE_PERMISSIONS) == {
        Role.ORG_ADMIN.value,
        Role.FINANCE_ANALYST.value,
        Role.AUDITOR.value,
    }


@pytest.mark.parametrize(
    "role,permission,expected",
    [
        ("org_admin", "uploads:create", True),
        ("org_admin", "users:manage", True),
        ("org_admin", "reviews:signoff", True),
        ("finance_analyst", "uploads:create", True),
        ("finance_analyst", "reports:create", True),
        ("finance_analyst", "users:manage", False),
        ("finance_analyst", "reviews:signoff", False),
        ("auditor", "uploads:read", True),
        ("auditor", "reports:read", True),
        ("auditor", "audit:read", True),
        ("auditor", "cost:read", True),
        ("auditor", "uploads:create", False),
        ("auditor", "jobs:create", False),
        ("auditor", "reviews:decide", False),
        ("auditor", "reports:create", False),
        ("unknown_role", "uploads:read", False),
    ],
)
def test_role_permission_matrix(role, permission, expected):
    assert has_permission([role], permission) is expected


def test_unknown_permission_is_denied():
    assert has_permission(["org_admin"], "unknown:permission") is False


def test_audit_events_cannot_be_modified_or_deleted():
    for role in ROLE_PERMISSIONS:
        assert has_permission(
            [role], "audit:update"
        ) is False
        assert has_permission(
            [role], "audit:delete"
        ) is False


def test_auditor_cannot_decide_reviews():
    assert not has_permission(
        ["auditor"],
        Permission.REVIEWS_DECIDE.value,
    )


def test_finance_analyst_can_decide_reviews():
    assert has_permission(
        ["finance_analyst"],
        Permission.REVIEWS_DECIDE.value,
    )


def test_permission_dependency_rejects_unauthorised_user():
    app = FastAPI()

    @app.get("/protected")
    def protected(
        user: dict = Depends(
            require_permission("uploads:create")
        ),
    ):
        return {"success": True}

    app.dependency_overrides[
        __import__(
            "app.api.deps.auth_deps",
            fromlist=["get_current_user"],
        ).get_current_user
    ] = lambda: {
        "_id": ObjectId(),
        "org_id": str(ObjectId()),
        "roles": ["auditor"],
    }

    response = TestClient(app).get("/protected")

    assert response.status_code == 403


def test_permission_dependency_accepts_authorised_user():
    app = FastAPI()

    @app.get("/protected")
    def protected(
        user: dict = Depends(
            require_permission("uploads:create")
        ),
    ):
        return {"success": True}

    from app.api.deps.auth_deps import get_current_user

    app.dependency_overrides[get_current_user] = lambda: {
        "_id": ObjectId(),
        "org_id": str(ObjectId()),
        "roles": ["finance_analyst"],
    }

    response = TestClient(app).get("/protected")

    assert response.status_code == 200
    assert response.json()["success"] is True


def test_tenant_context_comes_from_authenticated_user():
    app = FastAPI()

    expected_org_id = str(ObjectId())

    @app.get("/tenant")
    def tenant(
        org_id: str = Depends(get_current_org_id),
    ):
        return {"org_id": org_id}

    from app.api.deps.auth_deps import get_current_user

    app.dependency_overrides[get_current_user] = lambda: {
        "_id": ObjectId(),
        "org_id": expected_org_id,
        "roles": ["org_admin"],
    }

    response = TestClient(app).get(
        "/tenant",
        params={"org_id": str(ObjectId())},
    )

    assert response.status_code == 200
    assert response.json()["org_id"] == expected_org_id


def test_missing_tenant_context_is_rejected():
    app = FastAPI()

    @app.get("/tenant")
    def tenant(
        org_id: str = Depends(get_current_org_id),
    ):
        return {"org_id": org_id}

    from app.api.deps.auth_deps import get_current_user

    app.dependency_overrides[get_current_user] = lambda: {
        "_id": ObjectId(),
        "roles": ["org_admin"],
    }

    response = TestClient(app).get("/tenant")

    assert response.status_code == 403


from datetime import datetime, timedelta, timezone

import jwt
import pytest

from bson import ObjectId
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import auth_deps
from app.api.v1.routers.auth import router
from app.core.config import settings
from app.core.security import (
    _get_jwt_secret,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def make_test_token(**overrides):
    """Create a signed token with configurable claims."""

    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(ObjectId()),
        "org_id": str(ObjectId()),
        "roles": ["org_admin"],
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(minutes=15),
        "jti": "test-token",
    }
    payload.update(overrides)

    return jwt.encode(
        payload,
        _get_jwt_secret(),
        algorithm="HS256",
    )


@pytest.fixture
def client(monkeypatch):
    """Create an isolated application for authentication tests."""

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.state.mongodb_database = object()

    test_user = {
        "_id": ObjectId(),
        "org_id": str(ObjectId()),
        "email": "test@example.com",
        "roles": ["org_admin"],
        "status": "ACTIVE",
    }

    monkeypatch.setattr(
        auth_deps,
        "get_active_user",
        lambda database, *, user_id, org_id: (
            test_user
            if user_id == str(test_user["_id"])
            and org_id == test_user["org_id"]
            else None
        ),
    )

    return TestClient(app), test_user


def test_password_hashing_and_verification():
    password = "TestPassword123!"
    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword123!", hashed) is False


def test_valid_token_is_accepted():
    token = create_access_token(
        user_id=str(ObjectId()),
        org_id=str(ObjectId()),
        roles=["org_admin"],
    )

    payload = decode_access_token(token)

    assert payload["iss"] == settings.jwt_issuer
    assert payload["aud"] == settings.jwt_audience


def test_expired_token_is_rejected():
    token = make_test_token(
        exp=datetime.now(timezone.utc) - timedelta(minutes=1)
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)


def test_wrong_audience_token_is_rejected():
    token = make_test_token(aud="wrong-audience")

    with pytest.raises(jwt.InvalidAudienceError):
        decode_access_token(token)


def test_malformed_token_is_rejected():
    with pytest.raises(jwt.PyJWTError):
        decode_access_token("this-is-not-a-valid-jwt")


def test_protected_route_rejects_missing_token(client):
    test_client, _ = client

    response = test_client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Invalid or expired authentication credentials."
    )


def test_protected_route_accepts_valid_token(client):
    test_client, user = client

    token = create_access_token(
        user_id=str(user["_id"]),
        org_id=user["org_id"],
        roles=user["roles"],
    )

    response = test_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(user["_id"])
    assert response.json()["email"] == user["email"]


def test_protected_route_rejects_expired_token(client):
    test_client, _ = client
    token = make_test_token(
        exp=datetime.now(timezone.utc) - timedelta(minutes=1)
    )

    response = test_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_protected_route_rejects_wrong_audience(client):
    test_client, _ = client
    token = make_test_token(aud="wrong-audience")

    response = test_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_protected_route_rejects_malformed_token(client):
    test_client, _ = client

    response = test_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401


from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from pymongo.errors import PyMongoError

from app.api.v1.routers.auth import router as auth_router
from app.core.config import settings
from app.core.database import (
    close_mongo_client,
    create_mongo_client,
    ping_mongodb,
)
from app.observability.health import get_database_health


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage the MongoDB client lifecycle.

    Create one client at startup, verify connectivity,
    and close it during application shutdown.
    """

    app.state.mongodb_client = None
    app.state.mongodb_database = None
    app.state.mongodb_healthy = False

    try:
        client = create_mongo_client()
        app.state.mongodb_client = client
        app.state.mongodb_database = client[settings.mongodb_database]
        app.state.mongodb_healthy = ping_mongodb(client)

    except (PyMongoError, RuntimeError):
        app.state.mongodb_healthy = False

    try:
        yield
    finally:
        close_mongo_client(
            getattr(app.state, "mongodb_client", None)
        )
        app.state.mongodb_client = None
        app.state.mongodb_database = None
        app.state.mongodb_healthy = False


app = FastAPI(
    title=settings.app_name,
    description=(
        "Financial reconciliation and "
        "discrepancy investigation platform."
    ),
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)


# Register API routers
app.include_router(
    auth_router,
    prefix=settings.api_v1_prefix,
)


@app.get(
    f"{settings.api_v1_prefix}/health",
    tags=["Health"],
    summary="Check API health",
)
async def health_check() -> dict:
    """Check whether the API process is running."""

    return {
        "status": "healthy",
        "service": "recon-x-api",
        "api_version": "v1",
    }


@app.get(
    f"{settings.api_v1_prefix}/ready",
    tags=["Health"],
    summary="Check application readiness",
)
async def readiness_check(request: Request) -> dict:
    """Check whether the application and MongoDB are ready."""

    mongodb_healthy = get_database_health(request)

    if not mongodb_healthy:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "database": "unavailable",
            },
        )

    return {
        "status": "ready",
        "service": "recon-x-api",
        "database": "connected",
    }

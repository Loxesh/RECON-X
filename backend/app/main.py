
from fastapi import FastAPI

from app.core.config import settings


app = FastAPI(
    title=settings.app_name,
    description=(
        "Financial reconciliation and "
        "discrepancy investigation platform."
    ),
    version=settings.app_version,
    debug=settings.debug,
)


@app.get(
    f"{settings.api_v1_prefix}/health",
    tags=["Health"],
    summary="Check API health",
)
async def health_check() -> dict:
    """
    Return the health status of the RECON X API.
    """
    return {
        "status": "healthy",
        "service": "recon-x-api",
        "api_version": "v1",
    }

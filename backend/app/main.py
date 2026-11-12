
from fastapi import FastAPI

app = FastAPI(
    title="RECON X API",
    description=(
        "Financial reconciliation and "
        "discrepancy investigation platform."
    ),
    version="0.1.0",
)


@app.get(
    "/api/v1/health",
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

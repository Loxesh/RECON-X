
"""Central versioned API router."""

from fastapi import APIRouter

from app.api.v1.routers.auth import router as auth_router
from app.api.v1.routers.uploads import router as uploads_router
from app.api.v1.routers.reviews import router as reviews_router


api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(uploads_router)
api_router.include_router(reviews_router)

"""Main API router for v1 that groups all API endpoint routers."""

from typing import Dict
from fastapi import APIRouter

from app.api.v1.router import router as v1_router
from app.api.auth import router as auth_router

router = APIRouter()

api_router = APIRouter(prefix="/api")
api_router.include_router(v1_router)

router.include_router(auth_router)
router.include_router(api_router)


@router.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint for health check."""
    return {
        "message": "OSRS Diff API",
        "version": "1.0.0",
        "status": "running",
    }


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}

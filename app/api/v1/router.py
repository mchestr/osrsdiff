"""Main API router for v1 that groups all API endpoint routers."""

from fastapi import APIRouter

from app.api.v1.endpoints import history, players, statistics, system

# Main API router that groups all API endpoints
router = APIRouter(prefix="/v1")

# Include all API sub-routers in the main API router
router.include_router(players.router)
router.include_router(statistics.router)
router.include_router(history.router)
router.include_router(system.router)

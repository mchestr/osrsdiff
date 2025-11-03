"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.auth_endpoints import router as auth_router
from src.api.history import router as history_router
from src.api.players import router as players_router
from src.api.statistics import router as statistics_router
from src.api.system import router as system_router
from src.config import settings
from src.models.base import init_db
from src.services.startup import startup_service


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Handles startup and shutdown events for the FastAPI application.
    """
    # Startup
    await init_db()
    await startup_service.startup()

    yield

    # Shutdown
    # Add any cleanup code here if needed


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title="OSRS Diff API",
        description="Backend service for tracking Old School RuneScape character progression",
        version="1.0.0",
        debug=settings.debug,
        lifespan=lifespan,
        swagger_ui_oauth2_redirect_url="/docs/oauth2-redirect",
        swagger_ui_init_oauth={
            "usePkceWithAuthorizationCodeGrant": True,
        },
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(auth_router)
    app.include_router(players_router)
    app.include_router(statistics_router)
    app.include_router(history_router)
    app.include_router(system_router)

    return app


# Create the application instance
app = create_app()


@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint for health check."""
    return {
        "message": "OSRS Diff API",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}

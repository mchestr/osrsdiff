"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from logging.config import dictConfig
from typing import AsyncGenerator, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import router
from app.config import LogConfig, settings
from app.models.base import init_db
from app.services.startup import startup_service

dictConfig(LogConfig().model_dump())


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

    # Include the main API router
    app.include_router(router)

    return app


# Create the application instance
app = create_app()

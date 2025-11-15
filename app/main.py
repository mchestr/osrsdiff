import logging
from contextlib import asynccontextmanager
from logging.config import dictConfig
from pathlib import Path
from typing import AsyncGenerator

from aiohttp import ClientSession, ClientTimeout, DummyCookieJar
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import router
from app.config import LogConfig
from app.exceptions import BaseAPIException
from app.models.base import init_db
from app.services.auth import auth_service
from app.services.settings_cache import settings_cache
from app.services.startup import startup_service
from app.services.token_blacklist import token_blacklist_service

logger = logging.getLogger(__name__)

dictConfig(LogConfig().model_dump())


async def refresh_services_settings() -> None:
    """Refresh settings in all services that depend on them."""
    logger.info("Refreshing service settings...")
    try:
        # Refresh auth service settings
        auth_service._refresh_settings()
        logger.debug("Refreshed auth service settings")

        # Refresh token blacklist service settings
        token_blacklist_service._refresh_settings()
        logger.debug("Refreshed token blacklist service settings")

        logger.info("Service settings refreshed successfully")
    except Exception as e:
        logger.error(f"Failed to refresh service settings: {e}")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Handles startup and shutdown events for the FastAPI application.
    Creates and manages a shared aiohttp session for reuse across requests.
    """
    # Startup
    logger.info("Starting application lifecycle...")

    # Initialize database connection
    await init_db()

    # Run database migrations
    await startup_service.run_database_migrations()

    # Initialize settings from config.py (if they don't exist in DB)
    await startup_service.initialize_settings()

    # Load settings from database into cache
    await settings_cache.load_from_database()

    # Store settings cache in app state for access throughout the app lifecycle
    app.state.settings_cache = settings_cache
    logger.info("Settings cache loaded and stored in app state")

    # Refresh services that depend on settings
    await refresh_services_settings()

    # Create admin user (uses settings from cache)
    await startup_service.create_admin_user()

    # Create shared aiohttp session with DummyCookieJar to prevent cookie persistence
    # This avoids redirect issues caused by cookies being saved across requests
    timeout = ClientTimeout(total=30.0)
    session = ClientSession(
        timeout=timeout,
        headers={
            "User-Agent": "OSRSDiff/1.0.0 (https://github.com/mchestr/osrsdiff)"
        },
        cookie_jar=DummyCookieJar(),  # Don't save cookies across requests
    )
    app.state.osrs_http_session = session
    logger.info("Created shared aiohttp session for OSRS API")

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down application...")

    # Close the shared aiohttp session
    if hasattr(app.state, "osrs_http_session"):
        await app.state.osrs_http_session.close()
        logger.info("Closed shared aiohttp session")

    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    # Note: debug setting will be loaded during lifespan startup
    # For now, use config defaults (will be overridden after cache loads)
    from app.config import settings as config_defaults

    app = FastAPI(
        title="OSRS Diff API",
        description="Backend service for tracking Old School RuneScape character progression",
        version="1.0.0",
        debug=config_defaults.debug,
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

    # Include the main API router first
    app.include_router(router)

    # Serve static files and SPA from frontend build
    static_dir = Path(__file__).parent.parent / "static"
    if static_dir.exists():
        index_path = static_dir / "index.html"

        # Mount static assets (JS, CSS, images, etc.)
        app.mount(
            "/assets",
            StaticFiles(directory=str(static_dir / "assets")),
            name="static",
        )

        # Serve SPA index.html for root and all non-API routes
        @app.get("/")
        async def serve_index() -> FileResponse:
            """Serve SPA index.html at root."""
            if index_path.exists():
                return FileResponse(str(index_path))
            raise HTTPException(status_code=404, detail="Frontend not found")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str) -> FileResponse:
            """Serve SPA index.html for client-side routing, excluding API routes."""
            # Exclude API routes, docs, and static assets
            excluded_prefixes = (
                "api/",
                "auth/",
                "docs",
                "openapi.json",
                "assets/",
                "health",
            )
            if any(
                full_path.startswith(prefix) for prefix in excluded_prefixes
            ):
                raise HTTPException(status_code=404, detail="Not found")

            if index_path.exists():
                return FileResponse(str(index_path))
            raise HTTPException(status_code=404, detail="Frontend not found")

    # Add exception handlers for centralized exception handling
    @app.exception_handler(BaseAPIException)
    async def api_exception_handler(
        request: Request, exc: BaseAPIException
    ) -> JSONResponse:
        """Handle all BaseAPIException instances with consistent formatting."""
        logger.warning(
            f"API exception: {exc.status_code} - {exc.message} "
            f"(path: {request.url.path})"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "message": exc.message},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle unexpected exceptions."""
        logger.error(
            f"Unexpected exception: {type(exc).__name__}: {exc} "
            f"(path: {request.url.path})",
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "An unexpected error occurred",
                "message": "Internal server error",
            },
        )

    return app


# Create the application instance
app = create_app()

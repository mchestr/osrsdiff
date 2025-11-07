import logging
from pathlib import Path
from contextlib import asynccontextmanager
from logging.config import dictConfig
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import router
from app.config import LogConfig, settings
from app.exceptions import BaseAPIException
from app.models.base import init_db
from app.services.startup import startup_service

logger = logging.getLogger(__name__)

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

    # Include the main API router first
    app.include_router(router)

    # Serve static files and SPA from frontend build
    static_dir = Path(__file__).parent.parent / "static"
    if static_dir.exists():
        index_path = static_dir / "index.html"

        # Mount static assets (JS, CSS, images, etc.)
        app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="static")

        # Serve SPA index.html for root and all non-API routes
        @app.get("/")
        async def serve_index():
            """Serve SPA index.html at root."""
            if index_path.exists():
                return FileResponse(str(index_path))
            raise HTTPException(status_code=404, detail="Frontend not found")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            """Serve SPA index.html for client-side routing, excluding API routes."""
            # Exclude API routes, docs, and static assets
            excluded_prefixes = ("api/", "auth/", "docs", "openapi.json", "assets/", "health")
            if any(full_path.startswith(prefix) for prefix in excluded_prefixes):
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

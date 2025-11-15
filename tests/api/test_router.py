"""Tests for main API router."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.router import router


@pytest.fixture
def app():
    """Create FastAPI app for testing."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


class TestMainRouter:
    """Test cases for main API router."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_router_includes_auth_router(self, app):
        """Test that auth router is included."""
        routes = [route.path for route in app.routes]
        assert "/auth/login" in routes or any(
            "/auth" in route for route in routes
        )

    def test_router_includes_api_router(self, app):
        """Test that API v1 router is included."""
        routes = [route.path for route in app.routes]
        assert "/api/v1" in str(routes) or any(
            "/api" in route for route in routes
        )

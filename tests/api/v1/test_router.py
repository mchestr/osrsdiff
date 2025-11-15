"""Tests for API v1 router."""

import pytest
from fastapi import FastAPI

from app.api.v1.router import router


@pytest.fixture
def app():
    """Create FastAPI app for testing."""
    app = FastAPI()
    app.include_router(router)
    return app


class TestV1Router:
    """Test cases for API v1 router."""

    def test_router_has_v1_prefix(self, app):
        """Test that router has /v1 prefix."""
        routes = [route.path for route in app.routes]
        # Check that routes start with /v1
        v1_routes = [r for r in routes if r.startswith("/v1")]
        assert len(v1_routes) > 0

    def test_router_includes_players_endpoint(self, app):
        """Test that players router is included."""
        routes = [route.path for route in app.routes]
        # Players endpoint should be included
        assert any(
            "/v1/players" in route or "/players" in route for route in routes
        )

    def test_router_includes_statistics_endpoint(self, app):
        """Test that statistics router is included."""
        routes = [route.path for route in app.routes]
        # Statistics endpoints are under players, check for stats endpoint
        assert any("/stats" in route for route in routes)

    def test_router_includes_history_endpoint(self, app):
        """Test that history router is included."""
        routes = [route.path for route in app.routes]
        assert any(
            "/v1/history" in route or "/history" in route for route in routes
        )

    def test_router_includes_system_endpoint(self, app):
        """Test that system router is included."""
        routes = [route.path for route in app.routes]
        assert any(
            "/v1/system" in route or "/system" in route for route in routes
        )

    def test_router_includes_settings_endpoint(self, app):
        """Test that settings router is included."""
        routes = [route.path for route in app.routes]
        assert any(
            "/v1/settings" in route or "/settings" in route for route in routes
        )

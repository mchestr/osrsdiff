"""Tests for system administration API endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.auth import require_auth
from app.api.v1.endpoints.system import router
from app.models.base import get_db_session


@pytest.fixture
def mock_auth_user():
    """Mock authenticated user."""
    return {"username": "test_admin", "user_id": 1}


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    return AsyncMock()


@pytest.fixture
def app():
    """Create FastAPI app for testing with mocked dependencies."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app, mock_db_session, mock_auth_user):
    """Create test client with dependency overrides."""
    # Override dependencies
    app.dependency_overrides[get_db_session] = lambda: mock_db_session
    app.dependency_overrides[require_auth] = lambda: mock_auth_user

    return TestClient(app)


class TestSystemStats:
    """Test system statistics endpoint."""

    def test_get_database_stats_success(self, client, mock_db_session):
        """Test successful database stats retrieval."""
        from datetime import datetime

        # Mock database query results
        mock_db_session.execute.side_effect = [
            # total_players
            AsyncMock(scalar=lambda: 10),
            # active_players
            AsyncMock(scalar=lambda: 8),
            # total_records
            AsyncMock(scalar=lambda: 150),
            # oldest_record
            AsyncMock(scalar=lambda: datetime(2024, 1, 1)),
            # newest_record
            AsyncMock(scalar=lambda: datetime(2024, 11, 2)),
            # records_24h
            AsyncMock(scalar=lambda: 25),
            # records_7d
            AsyncMock(scalar=lambda: 100),
        ]

        response = client.get("/system/stats")

        assert response.status_code == 200
        data = response.json()

        assert data["total_players"] == 10
        assert data["active_players"] == 8
        assert data["inactive_players"] == 2
        assert data["total_hiscore_records"] == 150
        assert data["records_last_24h"] == 25
        assert data["records_last_7d"] == 100
        assert data["avg_records_per_player"] == 15.0

    def test_get_database_stats_unauthorized(self, app, mock_db_session):
        """Test database stats endpoint without authentication."""
        # Create client without auth override
        app.dependency_overrides[get_db_session] = lambda: mock_db_session
        # Don't override require_auth for this test
        client = TestClient(app)

        response = client.get("/system/stats")
        assert (
            response.status_code == 401
        )  # FastAPI returns 401 for missing auth


class TestSystemHealth:
    """Test system health endpoint."""

    def test_get_system_health_success(self, client, mock_db_session):
        """Test successful system health check."""
        # Mock successful database connection test
        mock_db_session.execute.return_value = AsyncMock()

        response = client.get("/system/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert data["database_connected"] is True
        assert "uptime_info" in data

    def test_get_system_health_db_error(self, client, mock_db_session):
        """Test system health check with database error."""
        # Mock database connection failure
        mock_db_session.execute.side_effect = Exception(
            "Database connection failed"
        )

        response = client.get("/system/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "degraded"
        assert data["database_connected"] is False


class TestPlayerDistribution:
    """Test player distribution endpoint."""

    def test_get_player_distribution_success(self, client, mock_db_session):
        """Test successful player distribution retrieval."""
        # Mock database query results for fetch intervals
        # The first execute() call returns a result with fetchall() method
        interval_result = AsyncMock()

        # Create mock row objects that support both attribute and index access
        class MockRow:
            def __init__(self, fetch_interval_minutes, count):
                self.fetch_interval_minutes = fetch_interval_minutes
                self.count = count

            def __getitem__(self, index):
                if index == 0:
                    return self.fetch_interval_minutes
                elif index == 1:
                    return self.count
                raise IndexError(f"Index {index} out of range")

        interval_rows = [
            MockRow(60, 5),
            MockRow(120, 3),
        ]
        interval_result.fetchall = lambda: interval_rows

        # Mock database query results for time ranges
        time_range_results = [
            AsyncMock(scalar=lambda: 2),  # never fetched
            AsyncMock(scalar=lambda: 1),  # last hour
            AsyncMock(scalar=lambda: 3),  # last 24h
            AsyncMock(scalar=lambda: 2),  # last week
            AsyncMock(scalar=lambda: 1),  # last month
            AsyncMock(scalar=lambda: 1),  # older
        ]

        mock_db_session.execute.side_effect = [
            interval_result
        ] + time_range_results

        response = client.get("/system/distribution")

        assert response.status_code == 200
        data = response.json()

        assert "by_fetch_interval" in data
        assert "by_last_fetch" in data
        assert data["never_fetched"] == 2
        assert "60min" in data["by_fetch_interval"]
        assert "120min" in data["by_fetch_interval"]

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


class TestTaskExecutions:
    """Test task execution tracking endpoint."""

    @pytest.mark.asyncio
    async def test_get_task_executions_success(
        self, app, mock_auth_user, test_session
    ):
        """Test successful retrieval of task executions."""
        from datetime import UTC, datetime

        from app.models.task_execution import (
            TaskExecution,
            TaskExecutionStatus,
        )

        # Create test task executions
        execution1 = TaskExecution(
            task_name="app.workers.fetch.fetch_player_hiscores_task",
            status=TaskExecutionStatus.SUCCESS,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            duration_seconds=1.5,
            task_args={"username": "test_user"},
            schedule_id="test_schedule_123",
            player_id=42,
            result_data={"status": "success"},
        )

        execution2 = TaskExecution(
            task_name="app.workers.fetch.fetch_player_hiscores_task",
            status=TaskExecutionStatus.FAILURE,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            duration_seconds=0.5,
            task_args={"username": "test_user2"},
            schedule_id="test_schedule_456",
            player_id=43,
            error_type="ValueError",
            error_message="Test error",
        )

        test_session.add(execution1)
        test_session.add(execution2)
        await test_session.commit()

        # Override dependencies
        from app.api.auth import require_auth
        from app.models.base import get_db_session

        app.dependency_overrides[get_db_session] = lambda: test_session
        app.dependency_overrides[require_auth] = lambda: mock_auth_user

        client = TestClient(app)

        response = client.get("/system/task-executions")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 2
        assert data["limit"] == 50
        assert data["offset"] == 0
        assert len(data["executions"]) == 2

        # Check first execution (should be most recent)
        exec1 = data["executions"][0]
        assert (
            exec1["task_name"]
            == "app.workers.fetch.fetch_player_hiscores_task"
        )
        assert exec1["status"] == "failure"
        assert exec1["player_id"] == 43

        # Check second execution
        exec2 = data["executions"][1]
        assert exec2["status"] == "success"
        assert exec2["player_id"] == 42

    @pytest.mark.asyncio
    async def test_get_task_executions_with_filters(
        self, app, mock_auth_user, test_session
    ):
        """Test filtering task executions by various criteria."""
        from datetime import UTC, datetime

        from app.models.task_execution import (
            TaskExecution,
            TaskExecutionStatus,
        )

        # Create test executions
        execution1 = TaskExecution(
            task_name="app.workers.fetch.fetch_player_hiscores_task",
            status=TaskExecutionStatus.SUCCESS,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            schedule_id="schedule_123",
            player_id=42,
        )

        execution2 = TaskExecution(
            task_name="app.workers.maintenance.schedule_verification_job",
            status=TaskExecutionStatus.SUCCESS,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            schedule_id="schedule_456",
        )

        execution3 = TaskExecution(
            task_name="app.workers.fetch.fetch_player_hiscores_task",
            status=TaskExecutionStatus.FAILURE,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            schedule_id="schedule_123",
            player_id=42,
        )

        test_session.add(execution1)
        test_session.add(execution2)
        test_session.add(execution3)
        await test_session.commit()

        from app.api.auth import require_auth
        from app.models.base import get_db_session

        app.dependency_overrides[get_db_session] = lambda: test_session
        app.dependency_overrides[require_auth] = lambda: mock_auth_user

        client = TestClient(app)

        # Filter by task_name
        response = client.get(
            "/system/task-executions?task_name=app.workers.fetch.fetch_player_hiscores_task"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert all(
            e["task_name"] == "app.workers.fetch.fetch_player_hiscores_task"
            for e in data["executions"]
        )

        # Filter by status
        response = client.get("/system/task-executions?status=failure")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["executions"][0]["status"] == "failure"

        # Filter by player_id
        response = client.get("/system/task-executions?player_id=42")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert all(e["player_id"] == 42 for e in data["executions"])

        # Filter by schedule_id
        response = client.get(
            "/system/task-executions?schedule_id=schedule_123"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert all(
            e["schedule_id"] == "schedule_123" for e in data["executions"]
        )

    @pytest.mark.asyncio
    async def test_get_task_executions_with_pagination(
        self, app, mock_auth_user, test_session
    ):
        """Test pagination of task executions."""
        from datetime import UTC, datetime

        from app.models.task_execution import (
            TaskExecution,
            TaskExecutionStatus,
        )

        # Create multiple executions
        for i in range(10):
            execution = TaskExecution(
                task_name="test_task",
                status=TaskExecutionStatus.SUCCESS,
                started_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
            )
            test_session.add(execution)

        await test_session.commit()

        from app.api.auth import require_auth
        from app.models.base import get_db_session

        app.dependency_overrides[get_db_session] = lambda: test_session
        app.dependency_overrides[require_auth] = lambda: mock_auth_user

        client = TestClient(app)

        # First page
        response = client.get("/system/task-executions?limit=5&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 10
        assert data["limit"] == 5
        assert data["offset"] == 0
        assert len(data["executions"]) == 5

        # Second page
        response = client.get("/system/task-executions?limit=5&offset=5")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 10
        assert data["limit"] == 5
        assert data["offset"] == 5
        assert len(data["executions"]) == 5

    def test_get_task_executions_invalid_status(self, client):
        """Test filtering with invalid status returns empty results."""
        response = client.get("/system/task-executions?status=invalid_status")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["executions"]) == 0

    def test_get_task_executions_unauthorized(self, app, mock_db_session):
        """Test task executions endpoint without authentication."""
        from app.models.base import get_db_session

        app.dependency_overrides[get_db_session] = lambda: mock_db_session
        # Don't override require_auth
        client = TestClient(app)

        response = client.get("/system/task-executions")
        assert response.status_code == 401

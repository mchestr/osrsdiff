"""Tests for system administration API endpoints."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.auth import require_auth
from app.api.auth_utils import require_admin
from app.api.v1.endpoints.system import router
from app.models.base import get_db_session


@pytest.fixture
def mock_auth_user():
    """Mock authenticated user."""
    return {"username": "test_admin", "user_id": 1}


@pytest.fixture
def mock_admin_user():
    """Mock admin user."""
    return {"username": "test_admin", "user_id": 1, "is_admin": True}


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    return AsyncMock()


@pytest.fixture
def app():
    """Create FastAPI app for testing with mocked dependencies."""
    from fastapi import Request
    from fastapi.responses import JSONResponse

    from app.exceptions import BaseAPIException

    app = FastAPI()
    app.include_router(router)

    # Add exception handler for BaseAPIException (like in main.py)
    @app.exception_handler(BaseAPIException)
    async def api_exception_handler(
        request: Request, exc: BaseAPIException
    ) -> JSONResponse:
        """Handle all BaseAPIException instances with consistent formatting."""
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "message": exc.message},
        )

    return app


@pytest.fixture
def client(app, mock_db_session, mock_auth_user):
    """Create test client with dependency overrides."""
    # Override dependencies
    app.dependency_overrides[get_db_session] = lambda: mock_db_session
    app.dependency_overrides[require_auth] = lambda: mock_auth_user

    return TestClient(app)


@pytest.fixture
def admin_client(app, mock_db_session, mock_admin_user):
    """Create test client with admin user dependency overrides."""
    # Override dependencies
    app.dependency_overrides[get_db_session] = lambda: mock_db_session
    app.dependency_overrides[require_auth] = lambda: mock_admin_user
    app.dependency_overrides[require_admin] = lambda: mock_admin_user

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


class TestSummaryGeneration:
    """Test cases for summary generation endpoints."""

    def test_generate_summaries_for_all_players(
        self, admin_client, mock_db_session
    ):
        """Test triggering summary generation tasks for all players."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from app.models.player import Player

        # Mock players query result
        mock_player1 = Player(id=1, username="player1", is_active=True)
        mock_player2 = Player(id=2, username="player2", is_active=True)

        mock_scalars_result = MagicMock()
        mock_scalars_result.all.return_value = [
            mock_player1,
            mock_player2,
        ]

        mock_players_result = MagicMock()
        mock_players_result.scalars.return_value = mock_scalars_result

        # Mock task result
        class MockTaskResult:
            def __init__(self, task_id):
                self.task_id = task_id

        with patch(
            "app.workers.tasks.generate_player_summary_task"
        ) as mock_task:
            # Mock the .kiq() method to return task results
            mock_task.kiq = AsyncMock(
                side_effect=[
                    MockTaskResult("task-id-1"),
                    MockTaskResult("task-id-2"),
                ]
            )

            # Mock database query for players
            async def mock_execute(query):
                if "is_active" in str(query):
                    return mock_players_result
                return AsyncMock()

            mock_db_session.execute = AsyncMock(side_effect=mock_execute)

            response = admin_client.post(
                "/system/generate-summaries",
                json={"player_id": None, "force_regenerate": False},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["tasks_triggered"] == 2
            assert len(data["task_ids"]) == 2
            assert "task-id-1" in data["task_ids"]
            assert "task-id-2" in data["task_ids"]

    def test_generate_summaries_for_specific_player(
        self, admin_client, mock_db_session
    ):
        """Test triggering summary generation task for specific player."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from app.models.player import Player

        # Mock player query result
        mock_player = Player(id=1, username="testplayer", is_active=True)
        mock_player_result = AsyncMock()
        mock_player_result.scalar_one_or_none.return_value = mock_player

        # Mock task result
        class MockTaskResult:
            def __init__(self, task_id):
                self.task_id = task_id

        with patch(
            "app.workers.tasks.generate_player_summary_task"
        ) as mock_task:
            # Mock the .kiq() method to return task result
            mock_task.kiq = AsyncMock(return_value=MockTaskResult("task-id-1"))

            # Mock database query for player
            async def mock_execute(query):
                if "id" in str(query) and "1" in str(query):
                    return mock_player_result
                return AsyncMock()

            mock_db_session.execute = AsyncMock(side_effect=mock_execute)

            response = admin_client.post(
                "/system/generate-summaries",
                json={"player_id": 1, "force_regenerate": False},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["tasks_triggered"] == 1
            assert len(data["task_ids"]) == 1
            assert data["task_ids"][0] == "task-id-1"

    def test_generate_summaries_player_not_found(
        self, admin_client, mock_db_session
    ):
        """Test triggering summary generation for non-existent player."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from sqlalchemy import select

        from app.models.player import Player

        # Mock player query result - player not found
        mock_player_result = MagicMock()
        mock_player_result.scalar_one_or_none.return_value = None

        # Mock database query for player - need to match the actual query structure
        async def mock_execute(query):
            # Check if this is a select query for Player with id filter
            query_str = str(query)
            # The query will be something like: SELECT ... FROM players WHERE players.id = :id_1
            if (
                hasattr(query, "column_descriptions")
                or "players" in query_str.lower()
            ):
                # Check if it's filtering by id=999
                if hasattr(query, "whereclause") or "999" in query_str:
                    return mock_player_result
            return MagicMock()

        mock_db_session.execute = AsyncMock(side_effect=mock_execute)

        response = admin_client.post(
            "/system/generate-summaries",
            json={"player_id": 999, "force_regenerate": False},
        )

        assert response.status_code == 404

    def test_generate_summaries_not_admin(
        self, app, mock_db_session, mock_auth_user
    ):
        """Test that non-admin users cannot generate summaries."""
        # Override require_auth but NOT require_admin
        # This allows require_admin to check is_admin and raise 403
        app.dependency_overrides[get_db_session] = lambda: mock_db_session
        app.dependency_overrides[require_auth] = lambda: mock_auth_user
        # Explicitly ensure require_admin is NOT overridden
        if require_admin in app.dependency_overrides:
            del app.dependency_overrides[require_admin]

        client = TestClient(app)

        response = client.post(
            "/system/generate-summaries",
            json={"player_id": None, "force_regenerate": False},
        )

        assert response.status_code == 403


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

        # Filter by task_name using search parameter
        response = client.get(
            "/system/task-executions?search=app.workers.fetch.fetch_player_hiscores_task"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert all(
            e["task_name"] == "app.workers.fetch.fetch_player_hiscores_task"
            for e in data["executions"]
        )

        # Filter by status using search parameter
        response = client.get("/system/task-executions?search=failure")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["executions"][0]["status"] == "failure"

        # Filter by schedule_id using search parameter
        response = client.get("/system/task-executions?search=schedule_123")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert all(
            e["schedule_id"] == "schedule_123" for e in data["executions"]
        )

        # Note: player_id filtering is not directly supported via search parameter
        # as it searches player username, not ID. This test would need a player
        # with username matching the ID or the endpoint would need to be updated.

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

    @pytest.mark.asyncio
    async def test_get_task_executions_invalid_status(
        self, app, mock_auth_user, test_session
    ):
        """Test filtering with invalid status returns empty results."""
        from app.api.auth import require_auth
        from app.models.base import get_db_session

        app.dependency_overrides[get_db_session] = lambda: test_session
        app.dependency_overrides[require_auth] = lambda: mock_auth_user

        client = TestClient(app)
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

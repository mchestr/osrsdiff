"""Tests for player management endpoints."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.api.players import get_player_service, router
from app.models.player import Player
from app.services.osrs_api import (
    OSRSAPIError,
)
from app.services.osrs_api import (
    PlayerNotFoundError as OSRSPlayerNotFoundError,
)
from app.services.player import (
    InvalidUsernameError,
    PlayerAlreadyExistsError,
    PlayerNotFoundServiceError,
    PlayerService,
)


def create_test_player(
    id: int,
    username: str,
    is_active: bool = True,
    fetch_interval_minutes: int = 60,
):
    """Create a test player with proper datetime fields."""
    player = Player(
        id=id,
        username=username,
        is_active=is_active,
        fetch_interval_minutes=fetch_interval_minutes,
    )
    # Set datetime fields manually since we're not using the database
    player.created_at = datetime.now(timezone.utc)
    player.last_fetched = None
    return player


@pytest.fixture
def mock_player_service():
    """Mock player service dependency."""
    return AsyncMock(spec=PlayerService)


@pytest.fixture
def mock_auth_user():
    """Mock authenticated user."""
    return {"username": "test_user", "user_id": 1}


@pytest.fixture
def app():
    """Create FastAPI app for testing with mocked dependencies."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app, mock_player_service, mock_auth_user):
    """Create test client with dependency overrides."""
    # Override dependencies
    app.dependency_overrides[get_player_service] = lambda: mock_player_service
    app.dependency_overrides[require_auth] = lambda: mock_auth_user

    return TestClient(app)


class TestPlayerEndpoints:
    """Test cases for player management endpoints."""

    def test_add_player_success(self, client, mock_player_service):
        """Test successful player addition."""
        # Mock player service response
        mock_player = create_test_player(1, "test_player")
        mock_player_service.add_player.return_value = mock_player

        response = client.post(
            "/players",
            json={"username": "test_player"},
            headers={"Authorization": "Bearer fake_token"},
        )

        assert response.status_code == 201
        data = response.json()

        assert data["id"] == 1
        assert data["username"] == "test_player"
        assert data["is_active"] is True
        assert data["fetch_interval_minutes"] == 60

        # Verify service was called correctly
        mock_player_service.add_player.assert_called_once_with("test_player")

    def test_add_player_invalid_username(self, client, mock_player_service):
        """Test adding player with invalid username."""
        mock_player_service.add_player.side_effect = InvalidUsernameError(
            "Invalid username format"
        )

        response = client.post(
            "/players",
            json={
                "username": "validname"  # Valid for Pydantic, but service will reject it
            },
            headers={"Authorization": "Bearer fake_token"},
        )

        assert response.status_code == 400
        assert "Invalid username format" in response.json()["detail"]

    def test_add_player_already_exists(self, client, mock_player_service):
        """Test adding player that already exists."""
        mock_player_service.add_player.side_effect = PlayerAlreadyExistsError(
            "Player already exists"
        )

        response = client.post(
            "/players",
            json={
                "username": "existing"  # Valid for Pydantic, but service will reject it
            },
            headers={"Authorization": "Bearer fake_token"},
        )

        assert response.status_code == 409
        assert "Player already exists" in response.json()["detail"]

    def test_add_player_not_found_in_osrs(self, client, mock_player_service):
        """Test adding player not found in OSRS hiscores."""
        mock_player_service.add_player.side_effect = OSRSPlayerNotFoundError(
            "Player not found in OSRS"
        )

        response = client.post(
            "/players",
            json={
                "username": "nonexistent"  # Valid for Pydantic, but service will reject it
            },
            headers={"Authorization": "Bearer fake_token"},
        )

        assert response.status_code == 404
        assert "Player not found in OSRS" in response.json()["detail"]

    def test_add_player_osrs_api_error(self, client, mock_player_service):
        """Test adding player when OSRS API is unavailable."""
        mock_player_service.add_player.side_effect = OSRSAPIError(
            "OSRS API unavailable"
        )

        response = client.post(
            "/players",
            json={"username": "test_player"},
            headers={"Authorization": "Bearer fake_token"},
        )

        assert response.status_code == 502
        assert "OSRS API unavailable" in response.json()["detail"]

    def test_add_player_without_auth(self, app, mock_player_service):
        """Test adding player without authentication."""
        # Create client without auth override
        app.dependency_overrides[get_player_service] = (
            lambda: mock_player_service
        )
        # Don't override require_auth for this test
        client = TestClient(app)

        response = client.post("/players", json={"username": "test_player"})

        assert (
            response.status_code == 401
        )  # FastAPI returns 401 for missing auth

    def test_remove_player_success(self, client, mock_player_service):
        """Test successful player removal."""
        mock_player_service.remove_player.return_value = True

        response = client.delete(
            "/players/test_player",
            headers={"Authorization": "Bearer fake_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "removed from tracking" in data["message"]

        # Verify service was called correctly
        mock_player_service.remove_player.assert_called_once_with(
            "test_player"
        )

    def test_remove_player_not_found(self, client, mock_player_service):
        """Test removing player that doesn't exist."""
        mock_player_service.remove_player.return_value = False

        response = client.delete(
            "/players/nonexistent_player",
            headers={"Authorization": "Bearer fake_token"},
        )

        assert response.status_code == 404
        assert "not found in tracking system" in response.json()["detail"]

    def test_remove_player_without_auth(self, app, mock_player_service):
        """Test removing player without authentication."""
        # Create client without auth override
        app.dependency_overrides[get_player_service] = (
            lambda: mock_player_service
        )
        # Don't override require_auth for this test
        client = TestClient(app)

        response = client.delete("/players/test_player")

        assert (
            response.status_code == 401
        )  # FastAPI returns 401 for missing auth

    def test_list_players_success(self, client, mock_player_service):
        """Test successful player listing."""
        # Mock player service response
        mock_players = [
            create_test_player(1, "player1", fetch_interval_minutes=60),
            create_test_player(2, "player2", fetch_interval_minutes=30),
        ]
        mock_player_service.list_players.return_value = mock_players

        response = client.get(
            "/players", headers={"Authorization": "Bearer fake_token"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total_count"] == 2
        assert len(data["players"]) == 2

        # Check first player
        player1 = data["players"][0]
        assert player1["id"] == 1
        assert player1["username"] == "player1"
        assert player1["is_active"] is True

        # Verify service was called correctly
        mock_player_service.list_players.assert_called_once_with(
            active_only=True
        )

    def test_list_players_include_inactive(self, client, mock_player_service):
        """Test listing players including inactive ones."""
        mock_players = [
            create_test_player(1, "active_player", is_active=True),
            create_test_player(2, "inactive_player", is_active=False),
        ]
        mock_player_service.list_players.return_value = mock_players

        response = client.get(
            "/players?active_only=false",
            headers={"Authorization": "Bearer fake_token"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total_count"] == 2
        assert len(data["players"]) == 2

        # Verify service was called correctly
        mock_player_service.list_players.assert_called_once_with(
            active_only=False
        )

    def test_list_players_empty(self, client, mock_player_service):
        """Test listing players when no players exist."""
        mock_player_service.list_players.return_value = []

        response = client.get(
            "/players", headers={"Authorization": "Bearer fake_token"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total_count"] == 0
        assert len(data["players"]) == 0

    def test_list_players_without_auth(self, app, mock_player_service):
        """Test listing players without authentication."""
        # Create client without auth override
        app.dependency_overrides[get_player_service] = (
            lambda: mock_player_service
        )
        # Don't override require_auth for this test
        client = TestClient(app)

        response = client.get("/players")

        assert (
            response.status_code == 401
        )  # FastAPI returns 401 for missing auth

    def test_add_player_validation_error(self, client, mock_player_service):
        """Test adding player with validation errors."""
        # Test empty username
        response = client.post(
            "/players",
            json={"username": ""},
            headers={"Authorization": "Bearer fake_token"},
        )

        assert response.status_code == 422  # Pydantic validation error

        # Test username too long
        response = client.post(
            "/players",
            json={"username": "this_username_is_too_long"},
            headers={"Authorization": "Bearer fake_token"},
        )

        assert response.status_code == 422  # Pydantic validation error

    def test_add_player_missing_username(self, client, mock_player_service):
        """Test adding player without username field."""
        response = client.post(
            "/players", json={}, headers={"Authorization": "Bearer fake_token"}
        )

        assert response.status_code == 422  # Pydantic validation error

    @patch("app.workers.tasks.fetch_player_hiscores_task")
    def test_trigger_manual_fetch_success(
        self, mock_task, client, mock_player_service
    ):
        """Test successful manual fetch trigger."""
        # Mock player service response
        mock_player = create_test_player(1, "test_player")
        mock_player_service.get_player.return_value = mock_player

        # Mock task result - create a simple object with task_id attribute
        class MockTaskResult:
            def __init__(self):
                self.task_id = "test-task-id-123"

        mock_task_result = MockTaskResult()

        # Mock the kiq method to return the task result asynchronously
        async def mock_kiq(*args, **kwargs):
            return mock_task_result

        mock_task.kiq = mock_kiq

        response = client.post(
            "/players/test_player/fetch",
            headers={"Authorization": "Bearer fake_token"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["task_id"] == "test-task-id-123"
        assert data["username"] == "test_player"
        assert data["status"] == "enqueued"
        assert data["estimated_completion_seconds"] == 15
        assert "Manual fetch task enqueued" in data["message"]

        # Verify service was called correctly
        mock_player_service.get_player.assert_called_once_with("test_player")

    @patch("app.workers.tasks.fetch_player_hiscores_task")
    def test_trigger_manual_fetch_player_not_found(
        self, mock_task, client, mock_player_service
    ):
        """Test manual fetch trigger for non-existent player."""
        mock_player_service.get_player.return_value = None

        response = client.post(
            "/players/nonexistent/fetch",
            headers={"Authorization": "Bearer fake_token"},
        )

        assert response.status_code == 404
        assert "not found in tracking system" in response.json()["detail"]

        # Verify service was called but task was not
        mock_player_service.get_player.assert_called_once_with("nonexistent")
        mock_task.kiq.assert_not_called()

    @patch("app.workers.tasks.fetch_player_hiscores_task")
    def test_trigger_manual_fetch_task_enqueue_error(
        self, mock_task, client, mock_player_service
    ):
        """Test manual fetch trigger when task enqueue fails."""
        # Mock player service response
        mock_player = create_test_player(1, "test_player")
        mock_player_service.get_player.return_value = mock_player

        # Mock task enqueue failure
        async def mock_kiq_error(*args, **kwargs):
            raise Exception("Task enqueue failed")

        mock_task.kiq = mock_kiq_error

        response = client.post(
            "/players/test_player/fetch",
            headers={"Authorization": "Bearer fake_token"},
        )

        assert response.status_code == 500
        assert "Failed to enqueue fetch task" in response.json()["detail"]

        # Verify service was called
        mock_player_service.get_player.assert_called_once_with("test_player")

    def test_trigger_manual_fetch_without_auth(self, app, mock_player_service):
        """Test manual fetch trigger without authentication."""
        # Create client without auth override
        app.dependency_overrides[get_player_service] = (
            lambda: mock_player_service
        )
        # Don't override require_auth for this test
        client = TestClient(app)

        response = client.post("/players/test_player/fetch")

        assert (
            response.status_code == 401
        )  # FastAPI returns 401 for missing auth


class TestPlayerMetadata:
    """Test player metadata endpoint."""

    @patch("app.api.players.get_db_session")
    def test_get_player_metadata_success(
        self, mock_get_db, client, mock_player_service
    ):
        """Test successful player metadata retrieval."""
        from datetime import datetime

        # Create mock database session
        mock_db_session = AsyncMock()
        mock_get_db.return_value = mock_db_session

        # Create test player
        test_player = create_test_player(1, "testuser")

        # Mock database queries in order
        mock_db_session.execute.side_effect = [
            # Player query
            AsyncMock(scalar_one_or_none=lambda: test_player),
            # Record count
            AsyncMock(scalar=lambda: 50),
            # First record
            AsyncMock(scalar=lambda: datetime(2024, 1, 1)),
            # Latest record
            AsyncMock(scalar=lambda: datetime(2024, 11, 2)),
            # Records last 24h
            AsyncMock(scalar=lambda: 5),
            # Records last 7d
            AsyncMock(scalar=lambda: 25),
        ]

        response = client.get("/players/testuser/metadata")

        assert response.status_code == 200
        data = response.json()

        assert data["username"] == "testuser"
        assert data["total_records"] == 50
        assert data["records_last_24h"] == 5
        assert data["records_last_7d"] == 25
        assert "avg_fetch_frequency_hours" in data

    @patch("app.api.players.get_db_session")
    def test_get_player_metadata_not_found(
        self, mock_get_db, client, mock_player_service
    ):
        """Test player metadata for non-existent player."""
        # Create mock database session
        mock_db_session = AsyncMock()
        mock_get_db.return_value = mock_db_session

        # Mock player not found
        mock_db_session.execute.return_value = AsyncMock(
            scalar_one_or_none=lambda: None
        )

        response = client.get("/players/nonexistent/metadata")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestPlayerActivation:
    """Test player activation/deactivation endpoints."""

    def test_deactivate_player_success(self, client, mock_player_service):
        """Test successful player deactivation."""
        mock_player_service.deactivate_player.return_value = True

        response = client.post("/players/testuser/deactivate")

        assert response.status_code == 200
        data = response.json()
        assert "deactivated" in data["message"]
        mock_player_service.deactivate_player.assert_called_once_with(
            "testuser"
        )

    def test_deactivate_player_not_found(self, client, mock_player_service):
        """Test deactivating non-existent player."""
        mock_player_service.deactivate_player.return_value = False

        response = client.post("/players/nonexistent/deactivate")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_reactivate_player_success(self, client, mock_player_service):
        """Test successful player reactivation."""
        mock_player_service.reactivate_player.return_value = True

        response = client.post("/players/testuser/reactivate")

        assert response.status_code == 200
        data = response.json()
        assert "reactivated" in data["message"]
        mock_player_service.reactivate_player.assert_called_once_with(
            "testuser"
        )

    def test_reactivate_player_not_found(self, client, mock_player_service):
        """Test reactivating non-existent player."""
        mock_player_service.reactivate_player.return_value = False

        response = client.post("/players/nonexistent/reactivate")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

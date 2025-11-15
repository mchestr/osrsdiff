"""Tests for player management endpoints."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.api.auth_utils import require_admin
from app.api.v1.endpoints.players import (
    get_db_session,
    get_player_service,
    router,
)
from app.exceptions import (
    BaseAPIException,
    OSRSPlayerNotFoundError,
    PlayerNotFoundError,
)
from app.models.player import Player
from app.services.osrs_api import (
    OSRSAPIError,
)
from app.services.player import (
    InvalidUsernameError,
    PlayerAlreadyExistsError,
    PlayerService,
)


def create_test_player(
    id: int,
    username: str,
    is_active: bool = True,
    fetch_interval_minutes: int = 1440,
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

    # Add exception handler for BaseAPIException
    @app.exception_handler(BaseAPIException)
    async def api_exception_handler(request, exc: BaseAPIException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "message": exc.message},
        )

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
        assert data["fetch_interval_minutes"] == 1440

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

    def test_get_player_metadata_success(self, client, mock_player_service):
        """Test successful player metadata retrieval."""
        from datetime import datetime

        # Create mock database session - use a regular object to avoid async wrapping
        from types import SimpleNamespace

        from app.models.base import get_db_session

        mock_db_session = SimpleNamespace()

        # Create test player
        test_player = create_test_player(1, "testuser")

        # Mock ensure_player_exists (async function)
        async def mock_ensure_player_exists(username):
            return test_player

        mock_player_service.ensure_player_exists = mock_ensure_player_exists

        # Mock database queries in order
        # Player query result (not used anymore but kept for compatibility)
        player_result = SimpleNamespace()
        player_result.scalar_one_or_none = lambda: test_player

        # Record count result - use a simple class to avoid async issues
        class MockResult:
            def __init__(self, value):
                self._value = value

            def scalar(self):
                return self._value

        count_result = MockResult(50)
        first_result = MockResult(datetime(2024, 1, 1, tzinfo=timezone.utc))
        latest_result = MockResult(datetime(2024, 11, 2, tzinfo=timezone.utc))
        records_24h_result = MockResult(5)
        records_7d_result = MockResult(25)

        # Create async execute function
        # Note: ensure_player_exists is called first, so the first execute() call
        # is for the record count query, not the player query
        call_count = [0]
        results_list = [
            count_result,  # Record count (first execute call)
            first_result,  # First record (second execute call)
            latest_result,  # Latest record (third execute call)
            records_24h_result,  # Records last 24h (fourth execute call)
            records_7d_result,  # Records last 7d (fifth execute call)
        ]

        async def mock_execute(query):
            result = results_list[call_count[0]]
            call_count[0] += 1
            return result

        mock_db_session.execute = mock_execute

        # Override the database dependency
        client.app.dependency_overrides[get_db_session] = (
            lambda: mock_db_session
        )

        response = client.get("/players/testuser/metadata")

        assert response.status_code == 200
        data = response.json()

        assert data["username"] == "testuser"
        assert data["total_records"] == 50
        assert data["records_last_24h"] == 5
        assert data["records_last_7d"] == 25
        assert "avg_fetch_frequency_hours" in data

    def test_get_player_metadata_not_found(self, client, mock_player_service):
        """Test player metadata for non-existent player."""
        from app.exceptions import OSRSPlayerNotFoundError

        # Mock ensure_player_exists to raise OSRSPlayerNotFoundError
        mock_player_service.ensure_player_exists.side_effect = (
            OSRSPlayerNotFoundError("nonexistent")
        )

        response = client.get("/players/nonexistent/metadata")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_get_player_metadata_no_auth_required(
        self, app, mock_player_service
    ):
        """Test that authentication is not required for metadata endpoint."""
        from datetime import datetime

        from app.models.base import get_db_session

        # Create client without auth override
        app.dependency_overrides[get_player_service] = (
            lambda: mock_player_service
        )
        # Don't override require_auth for this test
        client = TestClient(app)

        # Create mock database session - use a regular object to avoid async wrapping
        from types import SimpleNamespace

        mock_db_session = SimpleNamespace()

        # Create test player
        test_player = create_test_player(1, "testuser")

        # Mock ensure_player_exists (async function)
        async def mock_ensure_player_exists(username):
            return test_player

        mock_player_service.ensure_player_exists = mock_ensure_player_exists

        # Use a simple class to avoid async issues
        class MockResult:
            def __init__(self, value):
                self._value = value

            def scalar(self):
                return self._value

        count_result = MockResult(50)
        first_result = MockResult(datetime(2024, 1, 1, tzinfo=timezone.utc))
        latest_result = MockResult(datetime(2024, 11, 2, tzinfo=timezone.utc))
        records_24h_result = MockResult(5)
        records_7d_result = MockResult(25)

        # Create async execute function
        # Note: ensure_player_exists is called first, so the first execute() call
        # is for the record count query
        call_count = [0]
        results_list = [
            count_result,  # Record count (first execute call)
            first_result,  # First record (second execute call)
            latest_result,  # Latest record (third execute call)
            records_24h_result,  # Records last 24h (fourth execute call)
            records_7d_result,  # Records last 7d (fifth execute call)
        ]

        async def mock_execute(query):
            result = results_list[call_count[0]]
            call_count[0] += 1
            return result

        mock_db_session.execute = mock_execute

        # Override the database dependency
        app.dependency_overrides[get_db_session] = lambda: mock_db_session

        # Should work without auth headers
        response = client.get("/players/testuser/metadata")

        # Should succeed without authentication
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["total_records"] == 50


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


class TestPlayerSummary:
    """Test cases for player summary endpoints."""

    @pytest.fixture
    def mock_admin_user(self):
        """Mock admin user."""
        return {"username": "admin", "user_id": 1, "is_admin": True}

    @pytest.fixture
    def client_with_admin(self, app, mock_player_service, mock_admin_user):
        """Create test client with admin user."""
        app.dependency_overrides[get_player_service] = (
            lambda: mock_player_service
        )
        app.dependency_overrides[require_auth] = lambda: mock_admin_user
        app.dependency_overrides[require_admin] = lambda: mock_admin_user
        return TestClient(app)

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session for summary endpoints."""
        return AsyncMock()

    def test_get_player_summary_success(
        self, app, mock_db_session, mock_auth_user, mock_player_service
    ):
        """Test successful retrieval of player summary."""
        from datetime import datetime, timedelta, timezone

        from app.models.player import Player
        from app.models.player_summary import PlayerSummary

        # Mock database queries
        player = Player(id=1, username="testplayer")
        summary = PlayerSummary(
            id=1,
            player_id=1,
            period_start=datetime.now(timezone.utc) - timedelta(days=7),
            period_end=datetime.now(timezone.utc),
            summary_text="Test summary",
            generated_at=datetime.now(timezone.utc),
            model_used="gpt-4o-mini",
        )

        # Mock ensure_player_exists
        async def mock_ensure_player_exists(username):
            return player

        mock_player_service.ensure_player_exists = mock_ensure_player_exists

        async def mock_execute(query):
            if "player_summaries" in str(query).lower():
                return AsyncMock(scalar_one_or_none=lambda: summary)
            return AsyncMock()

        mock_db_session.execute = mock_execute
        app.dependency_overrides[get_db_session] = lambda: mock_db_session
        app.dependency_overrides[get_player_service] = (
            lambda: mock_player_service
        )
        app.dependency_overrides[require_auth] = lambda: mock_auth_user

        client = TestClient(app)
        response = client.get("/players/testplayer/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["summary_text"] == "Test summary"
        assert data["player_id"] == 1

    def test_get_player_summary_not_found(
        self, app, mock_db_session, mock_auth_user, mock_player_service
    ):
        """Test getting summary for non-existent player."""
        from app.exceptions import OSRSPlayerNotFoundError

        # Mock ensure_player_exists to raise OSRSPlayerNotFoundError
        mock_player_service.ensure_player_exists.side_effect = (
            OSRSPlayerNotFoundError("nonexistent")
        )

        app.dependency_overrides[get_db_session] = lambda: mock_db_session
        app.dependency_overrides[get_player_service] = (
            lambda: mock_player_service
        )
        app.dependency_overrides[require_auth] = lambda: mock_auth_user

        client = TestClient(app)
        response = client.get("/players/nonexistent/summary")

        assert response.status_code == 404

    def test_get_player_summary_no_summary(
        self, app, mock_db_session, mock_auth_user, mock_player_service
    ):
        """Test getting summary when player has no summary."""
        from app.models.player import Player

        player = Player(id=1, username="testplayer")

        # Mock ensure_player_exists
        async def mock_ensure_player_exists(username):
            return player

        mock_player_service.ensure_player_exists = mock_ensure_player_exists

        async def mock_execute(query):
            if "player_summaries" in str(query).lower():
                return AsyncMock(scalar_one_or_none=lambda: None)
            return AsyncMock()

        mock_db_session.execute = mock_execute
        app.dependency_overrides[get_db_session] = lambda: mock_db_session
        app.dependency_overrides[get_player_service] = (
            lambda: mock_player_service
        )
        app.dependency_overrides[require_auth] = lambda: mock_auth_user

        client = TestClient(app)
        response = client.get("/players/testplayer/summary")

        assert response.status_code == 200
        assert response.json() is None

    def test_generate_player_summary_success(
        self, app, mock_db_session, mock_admin_user
    ):
        """Test successful summary generation."""
        from datetime import datetime, timedelta, timezone
        from unittest.mock import AsyncMock, MagicMock, patch

        from app.models.player import Player
        from app.models.player_summary import PlayerSummary

        player = Player(id=1, username="testplayer")

        async def mock_execute(query):
            if "players" in str(query).lower():
                return AsyncMock(scalar_one_or_none=lambda: player)
            return AsyncMock()

        mock_db_session.execute = mock_execute
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        app.dependency_overrides[get_db_session] = lambda: mock_db_session
        app.dependency_overrides[require_auth] = lambda: mock_admin_user
        app.dependency_overrides[require_admin] = lambda: mock_admin_user

        # Patch get_summary_service at the module level where it's imported
        with patch(
            "app.services.summary.get_summary_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_summary = PlayerSummary(
                id=1,
                player_id=1,
                period_start=datetime.now(timezone.utc) - timedelta(days=7),
                period_end=datetime.now(timezone.utc),
                summary_text="Generated summary",
                generated_at=datetime.now(timezone.utc),
            )
            mock_service.generate_summary_for_player = AsyncMock(
                return_value=mock_summary
            )
            mock_get_service.return_value = mock_service

            client = TestClient(app)
            response = client.post(
                "/players/testplayer/summary", json={"force_regenerate": False}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["summary_text"] == "Generated summary"

    def test_generate_player_summary_not_admin(self, app, mock_auth_user):
        """Test that non-admin users cannot generate summaries."""
        from app.api.v1.endpoints.players import get_db_session

        app.dependency_overrides[require_auth] = lambda: mock_auth_user

        client = TestClient(app)
        response = client.post(
            "/players/testplayer/summary", json={"force_regenerate": False}
        )

        assert response.status_code == 403

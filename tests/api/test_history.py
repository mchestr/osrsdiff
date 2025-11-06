"""Tests for history API endpoints."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.auth import require_auth
from app.api.history import get_history_service, router
from app.models.hiscore import HiscoreRecord
from app.models.player import Player
from app.services.history import (
    BossProgress,
    HistoryService,
    HistoryServiceError,
    InsufficientDataError,
    PlayerNotFoundError,
    ProgressAnalysis,
    SkillProgress,
)


def create_test_player(id: int, username: str):
    """Create a test player with proper datetime fields."""
    player = Player(
        id=id, username=username, is_active=True, fetch_interval_minutes=60
    )
    player.created_at = datetime.now(timezone.utc)
    player.last_fetched = None
    return player


def create_test_hiscore_record(
    id: int, player: Player, fetched_at: datetime = None
):
    """Create a test hiscore record."""
    if fetched_at is None:
        fetched_at = datetime.now(timezone.utc)

    record = HiscoreRecord(
        id=id,
        player_id=player.id,
        fetched_at=fetched_at,
        overall_rank=1000,
        overall_level=1500,
        overall_experience=50000000,
        skills_data={
            "attack": {"rank": 500, "level": 99, "experience": 13034431},
            "defence": {"rank": 600, "level": 90, "experience": 5346332},
            "strength": {"rank": 400, "level": 99, "experience": 13034431},
        },
        bosses_data={
            "zulrah": {"rank": 1000, "kill_count": 500},
            "vorkath": {"rank": 2000, "kill_count": 200},
        },
    )
    record.player = player
    return record


@pytest.fixture
def mock_history_service():
    """Mock history service dependency."""
    return AsyncMock(spec=HistoryService)


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
def client(app, mock_history_service, mock_auth_user):
    """Create test client with dependency overrides."""
    # Override dependencies
    app.dependency_overrides[get_history_service] = (
        lambda: mock_history_service
    )
    app.dependency_overrides[require_auth] = lambda: mock_auth_user

    return TestClient(app)


class TestHistoryEndpoints:
    """Test cases for history API endpoints."""

    def test_get_player_history_success_with_dates(
        self, client, mock_history_service
    ):
        """Test successful retrieval of player history with specific dates."""
        # Create test data
        player = create_test_player(1, "test_player")
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

        start_record = create_test_hiscore_record(1, player, start_date)
        end_record = create_test_hiscore_record(2, player, end_date)

        # Create mock progress analysis
        progress = ProgressAnalysis(
            username="test_player",
            start_date=start_date,
            end_date=end_date,
            start_record=start_record,
            end_record=end_record,
        )

        mock_history_service.get_progress_between_dates.return_value = progress

        response = client.get(
            "/players/test_player/history"
            "?start_date=2024-01-01T00:00:00Z"
            "&end_date=2024-01-31T23:59:59Z",
            headers={"Authorization": "Bearer fake_token"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["username"] == "test_player"
        assert "period" in data
        assert "records" in data
        assert "progress" in data
        assert "rates" in data

        # Verify service was called correctly
        mock_history_service.get_progress_between_dates.assert_called_once()
        call_args = mock_history_service.get_progress_between_dates.call_args
        assert call_args[0][0] == "test_player"  # username
        assert call_args[0][1].year == 2024  # start_date
        assert call_args[0][1].month == 1
        assert call_args[0][1].day == 1
        assert call_args[0][2].year == 2024  # end_date
        assert call_args[0][2].month == 1
        assert call_args[0][2].day == 31

    def test_get_player_history_success_with_days(
        self, client, mock_history_service
    ):
        """Test successful retrieval of player history using days parameter."""
        # Create test data
        player = create_test_player(1, "test_player")
        now = datetime.now(timezone.utc)
        start_date = now - timedelta(days=7)

        start_record = create_test_hiscore_record(1, player, start_date)
        end_record = create_test_hiscore_record(2, player, now)

        # Create mock progress analysis
        progress = ProgressAnalysis(
            username="test_player",
            start_date=start_date,
            end_date=now,
            start_record=start_record,
            end_record=end_record,
        )

        mock_history_service.get_progress_between_dates.return_value = progress

        response = client.get(
            "/players/test_player/history?days=7",
            headers={"Authorization": "Bearer fake_token"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["username"] == "test_player"

        # Verify service was called with approximately 7 days difference
        mock_history_service.get_progress_between_dates.assert_called_once()
        call_args = mock_history_service.get_progress_between_dates.call_args
        start_arg = call_args[0][1]
        end_arg = call_args[0][2]
        days_diff = (end_arg - start_arg).days
        assert 6 <= days_diff <= 7  # Allow for small timing differences

    def test_get_player_history_default_30_days(
        self, client, mock_history_service
    ):
        """Test default behavior (30 days) when no parameters provided."""
        # Create test data
        player = create_test_player(1, "test_player")
        now = datetime.now(timezone.utc)
        start_date = now - timedelta(days=30)

        start_record = create_test_hiscore_record(1, player, start_date)
        end_record = create_test_hiscore_record(2, player, now)

        # Create mock progress analysis
        progress = ProgressAnalysis(
            username="test_player",
            start_date=start_date,
            end_date=now,
            start_record=start_record,
            end_record=end_record,
        )

        mock_history_service.get_progress_between_dates.return_value = progress

        response = client.get(
            "/players/test_player/history",
            headers={"Authorization": "Bearer fake_token"},
        )

        assert response.status_code == 200

        # Verify service was called with approximately 30 days difference
        mock_history_service.get_progress_between_dates.assert_called_once()
        call_args = mock_history_service.get_progress_between_dates.call_args
        start_arg = call_args[0][1]
        end_arg = call_args[0][2]
        days_diff = (end_arg - start_arg).days
        assert 29 <= days_diff <= 30  # Allow for small timing differences

    def test_get_player_history_invalid_date_format(
        self, client, mock_history_service
    ):
        """Test handling of invalid date format."""
        response = client.get(
            "/players/test_player/history?start_date=invalid-date",
            headers={"Authorization": "Bearer fake_token"},
        )

        assert response.status_code == 400
        assert "Invalid start_date format" in response.json()["detail"]

    def test_get_player_history_start_after_end(
        self, client, mock_history_service
    ):
        """Test handling of start date after end date."""
        response = client.get(
            "/players/test_player/history"
            "?start_date=2024-01-31T00:00:00Z"
            "&end_date=2024-01-01T00:00:00Z",
            headers={"Authorization": "Bearer fake_token"},
        )

        assert response.status_code == 400
        assert (
            "Start date must be before end date" in response.json()["detail"]
        )

    def test_get_player_history_date_range_too_large(
        self, client, mock_history_service
    ):
        """Test handling of date range exceeding 365 days."""
        response = client.get(
            "/players/test_player/history"
            "?start_date=2023-01-01T00:00:00Z"
            "&end_date=2024-01-02T00:00:00Z",
            headers={"Authorization": "Bearer fake_token"},
        )

        assert response.status_code == 400
        assert "Date range cannot exceed 365 days" in response.json()["detail"]

    def test_get_player_history_player_not_found(
        self, client, mock_history_service
    ):
        """Test handling of non-existent player."""
        mock_history_service.get_progress_between_dates.side_effect = (
            PlayerNotFoundError("Player 'nonexistent' not found")
        )

        response = client.get(
            "/players/nonexistent/history",
            headers={"Authorization": "Bearer fake_token"},
        )

        assert response.status_code == 404
        assert "not found in tracking system" in response.json()["detail"]

    def test_get_player_history_insufficient_data(
        self, client, mock_history_service
    ):
        """Test handling of insufficient data error."""
        mock_history_service.get_progress_between_dates.side_effect = (
            InsufficientDataError("Insufficient data for progress analysis")
        )

        response = client.get(
            "/players/test_player/history",
            headers={"Authorization": "Bearer fake_token"},
        )

        assert response.status_code == 422
        assert "Insufficient data" in response.json()["detail"]

    def test_get_player_history_service_error(
        self, client, mock_history_service
    ):
        """Test handling of history service errors."""
        mock_history_service.get_progress_between_dates.side_effect = (
            HistoryServiceError("Database connection failed")
        )

        response = client.get(
            "/players/test_player/history",
            headers={"Authorization": "Bearer fake_token"},
        )

        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]

    def test_get_skill_progress_success(self, client, mock_history_service):
        """Test successful retrieval of skill progress."""
        # Create test data
        player = create_test_player(1, "test_player")
        records = [
            create_test_hiscore_record(
                1, player, datetime.now(timezone.utc) - timedelta(days=7)
            ),
            create_test_hiscore_record(2, player, datetime.now(timezone.utc)),
        ]

        # Create mock skill progress
        skill_progress = SkillProgress(
            username="test_player",
            skill_name="attack",
            records=records,
            days=7,
        )

        mock_history_service.get_skill_progress.return_value = skill_progress

        response = client.get(
            "/players/test_player/history/skills/attack?days=7",
            headers={"Authorization": "Bearer fake_token"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["username"] == "test_player"
        assert data["skill"] == "attack"
        assert data["period_days"] == 7
        assert "progress" in data
        assert "timeline" in data

        # Verify service was called correctly
        mock_history_service.get_skill_progress.assert_called_once_with(
            "test_player", "attack", 7
        )

    def test_get_skill_progress_default_days(
        self, client, mock_history_service
    ):
        """Test skill progress with default days parameter."""
        # Create mock skill progress
        player = create_test_player(1, "test_player")
        records = [create_test_hiscore_record(1, player)]
        skill_progress = SkillProgress(
            username="test_player",
            skill_name="defence",
            records=records,
            days=30,
        )

        mock_history_service.get_skill_progress.return_value = skill_progress

        response = client.get(
            "/players/test_player/history/skills/defence",
            headers={"Authorization": "Bearer fake_token"},
        )

        assert response.status_code == 200

        # Verify service was called with default 30 days
        mock_history_service.get_skill_progress.assert_called_once_with(
            "test_player", "defence", 30
        )

    def test_get_skill_progress_invalid_days(
        self, client, mock_history_service
    ):
        """Test skill progress with invalid days parameter."""
        response = client.get(
            "/players/test_player/history/skills/attack?days=0",
            headers={"Authorization": "Bearer fake_token"},
        )

        assert response.status_code == 422  # Validation error

    def test_get_skill_progress_days_too_large(
        self, client, mock_history_service
    ):
        """Test skill progress with days parameter exceeding limit."""
        response = client.get(
            "/players/test_player/history/skills/attack?days=400",
            headers={"Authorization": "Bearer fake_token"},
        )

        assert response.status_code == 422  # Validation error

    def test_get_skill_progress_empty_skill_name(
        self, client, mock_history_service
    ):
        """Test skill progress with empty skill name."""
        response = client.get(
            "/players/test_player/history/skills/ ",
            headers={"Authorization": "Bearer fake_token"},
        )

        assert response.status_code == 400
        assert "Skill name cannot be empty" in response.json()["detail"]

    def test_get_skill_progress_player_not_found(
        self, client, mock_history_service
    ):
        """Test skill progress for non-existent player."""
        mock_history_service.get_skill_progress.side_effect = (
            PlayerNotFoundError("Player 'nonexistent' not found")
        )

        response = client.get(
            "/players/nonexistent/history/skills/attack",
            headers={"Authorization": "Bearer fake_token"},
        )

        assert response.status_code == 404
        assert "not found in tracking system" in response.json()["detail"]

    def test_get_skill_progress_insufficient_data(
        self, client, mock_history_service
    ):
        """Test skill progress with insufficient data."""
        mock_history_service.get_skill_progress.side_effect = (
            InsufficientDataError(
                "Insufficient attack data for progress analysis"
            )
        )

        response = client.get(
            "/players/test_player/history/skills/attack",
            headers={"Authorization": "Bearer fake_token"},
        )

        assert response.status_code == 422
        assert "Insufficient attack data" in response.json()["detail"]

    def test_get_boss_progress_success(self, client, mock_history_service):
        """Test successful retrieval of boss progress."""
        # Create test data
        player = create_test_player(1, "test_player")
        records = [
            create_test_hiscore_record(
                1, player, datetime.now(timezone.utc) - timedelta(days=14)
            ),
            create_test_hiscore_record(2, player, datetime.now(timezone.utc)),
        ]

        # Create mock boss progress
        boss_progress = BossProgress(
            username="test_player",
            boss_name="zulrah",
            records=records,
            days=14,
        )

        mock_history_service.get_boss_progress.return_value = boss_progress

        response = client.get(
            "/players/test_player/history/bosses/zulrah?days=14",
            headers={"Authorization": "Bearer fake_token"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["username"] == "test_player"
        assert data["boss"] == "zulrah"
        assert data["period_days"] == 14
        assert "progress" in data
        assert "timeline" in data

        # Verify service was called correctly
        mock_history_service.get_boss_progress.assert_called_once_with(
            "test_player", "zulrah", 14
        )

    def test_get_boss_progress_default_days(
        self, client, mock_history_service
    ):
        """Test boss progress with default days parameter."""
        # Create mock boss progress
        player = create_test_player(1, "test_player")
        records = [create_test_hiscore_record(1, player)]
        boss_progress = BossProgress(
            username="test_player",
            boss_name="vorkath",
            records=records,
            days=30,
        )

        mock_history_service.get_boss_progress.return_value = boss_progress

        response = client.get(
            "/players/test_player/history/bosses/vorkath",
            headers={"Authorization": "Bearer fake_token"},
        )

        assert response.status_code == 200

        # Verify service was called with default 30 days
        mock_history_service.get_boss_progress.assert_called_once_with(
            "test_player", "vorkath", 30
        )

    def test_get_boss_progress_empty_boss_name(
        self, client, mock_history_service
    ):
        """Test boss progress with empty boss name."""
        response = client.get(
            "/players/test_player/history/bosses/ ",
            headers={"Authorization": "Bearer fake_token"},
        )

        assert response.status_code == 400
        assert "Boss name cannot be empty" in response.json()["detail"]

    def test_get_boss_progress_player_not_found(
        self, client, mock_history_service
    ):
        """Test boss progress for non-existent player."""
        mock_history_service.get_boss_progress.side_effect = (
            PlayerNotFoundError("Player 'nonexistent' not found")
        )

        response = client.get(
            "/players/nonexistent/history/bosses/zulrah",
            headers={"Authorization": "Bearer fake_token"},
        )

        assert response.status_code == 404
        assert "not found in tracking system" in response.json()["detail"]

    def test_get_boss_progress_insufficient_data(
        self, client, mock_history_service
    ):
        """Test boss progress with insufficient data."""
        mock_history_service.get_boss_progress.side_effect = (
            InsufficientDataError(
                "Insufficient zulrah data for progress analysis"
            )
        )

        response = client.get(
            "/players/test_player/history/bosses/zulrah",
            headers={"Authorization": "Bearer fake_token"},
        )

        assert response.status_code == 422
        assert "Insufficient zulrah data" in response.json()["detail"]

    def test_authentication_required_history(
        self, client, mock_history_service
    ):
        """Test that authentication is required for history endpoint."""
        # Remove auth override to test without authentication
        app = client.app
        del app.dependency_overrides[require_auth]

        response = client.get("/players/test_player/history")

        # Without auth, FastAPI should return 401 for missing dependency
        assert response.status_code == 401

    def test_authentication_required_skill_progress(
        self, client, mock_history_service
    ):
        """Test that authentication is required for skill progress endpoint."""
        # Remove auth override to test without authentication
        app = client.app
        del app.dependency_overrides[require_auth]

        response = client.get("/players/test_player/history/skills/attack")

        # Without auth, FastAPI should return 401 for missing dependency
        assert response.status_code == 401

    def test_authentication_required_boss_progress(
        self, client, mock_history_service
    ):
        """Test that authentication is required for boss progress endpoint."""
        # Remove auth override to test without authentication
        app = client.app
        del app.dependency_overrides[require_auth]

        response = client.get("/players/test_player/history/bosses/zulrah")

        # Without auth, FastAPI should return 401 for missing dependency
        assert response.status_code == 401

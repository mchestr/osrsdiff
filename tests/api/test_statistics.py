"""Tests for statistics API endpoints."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.auth import require_auth
from src.api.statistics import get_statistics_service, router
from src.models.hiscore import HiscoreRecord
from src.models.player import Player
from src.services.statistics import (
    NoDataAvailableError,
    PlayerNotFoundError,
    StatisticsService,
    StatisticsServiceError,
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
            "hitpoints": {"rank": 300, "level": 99, "experience": 13034431},
            "prayer": {"rank": 800, "level": 70, "experience": 737627},
            "ranged": {"rank": 200, "level": 99, "experience": 13034431},
            "magic": {"rank": 100, "level": 99, "experience": 13034431},
        },
        bosses_data={
            "zulrah": {"rank": 1000, "kill_count": 500},
            "vorkath": {"rank": 2000, "kill_count": 200},
        },
    )
    record.player = player
    return record


@pytest.fixture
def mock_statistics_service():
    """Mock statistics service dependency."""
    return AsyncMock(spec=StatisticsService)


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
def client(app, mock_statistics_service, mock_auth_user):
    """Create test client with dependency overrides."""
    # Override dependencies
    app.dependency_overrides[get_statistics_service] = (
        lambda: mock_statistics_service
    )
    app.dependency_overrides[require_auth] = lambda: mock_auth_user

    return TestClient(app)


class TestStatisticsEndpoints:
    """Test cases for statistics API endpoints."""

    def test_get_player_stats_success(self, client, mock_statistics_service):
        """Test successful retrieval of player statistics."""
        # Create test data
        player = create_test_player(1, "test_player")
        record = create_test_hiscore_record(1, player)

        # Mock service responses
        mock_statistics_service.get_current_stats.return_value = record
        mock_statistics_service.format_stats_response.return_value = {
            "username": "test_player",
            "fetched_at": record.fetched_at.isoformat(),
            "overall": {
                "rank": 1000,
                "level": 1500,
                "experience": 50000000,
            },
            "combat_level": 133,
            "skills": {
                "attack": {"rank": 500, "level": 99, "experience": 13034431},
                "defence": {"rank": 600, "level": 90, "experience": 5346332},
            },
            "bosses": {
                "zulrah": {"rank": 1000, "kill_count": 500},
                "vorkath": {"rank": 2000, "kill_count": 200},
            },
            "metadata": {
                "total_skills": 7,
                "total_bosses": 2,
                "record_id": 1,
            },
        }

        response = client.get(
            "/players/test_player/stats",
            headers={"Authorization": "Bearer fake_token"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["username"] == "test_player"
        assert data["fetched_at"] is not None
        assert data["overall"]["rank"] == 1000
        assert data["overall"]["level"] == 1500
        assert data["overall"]["experience"] == 50000000
        assert data["combat_level"] == 133
        assert "attack" in data["skills"]
        assert "zulrah" in data["bosses"]
        assert data["metadata"]["total_skills"] == 7
        assert data["metadata"]["total_bosses"] == 2
        assert data["error"] is None

        # Verify service was called correctly
        mock_statistics_service.get_current_stats.assert_called_once_with(
            "test_player"
        )
        mock_statistics_service.format_stats_response.assert_called_once_with(
            record, "test_player"
        )

    def test_get_player_stats_no_data(self, client, mock_statistics_service):
        """Test getting stats for player with no data."""
        # Mock service to return None (no data)
        mock_statistics_service.get_current_stats.return_value = None

        response = client.get(
            "/players/test_player/stats",
            headers={"Authorization": "Bearer fake_token"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["username"] == "test_player"
        assert data["fetched_at"] is None
        assert data["overall"] is None
        assert data["combat_level"] is None
        assert data["skills"] == {}
        assert data["bosses"] == {}
        assert data["error"] == "No data available"
        assert data["metadata"]["total_skills"] == 0
        assert data["metadata"]["total_bosses"] == 0
        assert data["metadata"]["record_id"] is None

    def test_get_player_stats_player_not_found(
        self, client, mock_statistics_service
    ):
        """Test getting stats for non-existent player."""
        mock_statistics_service.get_current_stats.side_effect = (
            PlayerNotFoundError("Player 'nonexistent' not found")
        )

        response = client.get(
            "/players/nonexistent/stats",
            headers={"Authorization": "Bearer fake_token"},
        )

        assert response.status_code == 404
        assert "not found in tracking system" in response.json()["detail"]

    def test_get_player_stats_service_error(
        self, client, mock_statistics_service
    ):
        """Test handling of statistics service errors."""
        mock_statistics_service.get_current_stats.side_effect = (
            StatisticsServiceError("Database connection failed")
        )

        response = client.get(
            "/players/test_player/stats",
            headers={"Authorization": "Bearer fake_token"},
        )

        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]

    def test_get_multiple_player_stats_success(
        self, client, mock_statistics_service
    ):
        """Test successful retrieval of multiple player statistics."""
        # Create test data
        player1 = create_test_player(1, "player1")
        player2 = create_test_player(2, "player2")
        record1 = create_test_hiscore_record(1, player1)

        # Mock service responses
        stats_map = {
            "player1": record1,
            "player2": None,  # No data
            "nonexistent": None,  # Not found
        }
        mock_statistics_service.get_multiple_stats.return_value = stats_map
        mock_statistics_service.format_multiple_stats_response.return_value = {
            "players": {
                "player1": {
                    "username": "player1",
                    "fetched_at": record1.fetched_at.isoformat(),
                    "overall": {
                        "rank": 1000,
                        "level": 1500,
                        "experience": 50000000,
                    },
                    "combat_level": 133,
                    "skills": {
                        "attack": {
                            "rank": 500,
                            "level": 99,
                            "experience": 13034431,
                        }
                    },
                    "bosses": {"zulrah": {"rank": 1000, "kill_count": 500}},
                    "metadata": {
                        "total_skills": 7,
                        "total_bosses": 2,
                        "record_id": 1,
                    },
                },
                "player2": {
                    "username": "player2",
                    "fetched_at": None,
                    "overall": None,
                    "combat_level": None,
                    "skills": {},
                    "bosses": {},
                    "metadata": {
                        "total_skills": 0,
                        "total_bosses": 0,
                        "record_id": None,
                    },
                    "error": "No data available",
                },
                "nonexistent": {
                    "username": "nonexistent",
                    "fetched_at": None,
                    "overall": None,
                    "combat_level": None,
                    "skills": {},
                    "bosses": {},
                    "metadata": {
                        "total_skills": 0,
                        "total_bosses": 0,
                        "record_id": None,
                    },
                    "error": "No data available",
                },
            },
            "metadata": {
                "total_requested": 3,
                "total_found": 1,
                "total_missing": 2,
            },
        }

        response = client.get(
            "/players/stats?usernames=player1&usernames=player2&usernames=nonexistent",
            headers={"Authorization": "Bearer fake_token"},
        )

        assert response.status_code == 200
        data = response.json()

        assert "players" in data
        assert "metadata" in data

        # Check players data
        players = data["players"]
        assert len(players) == 3

        # Player with data
        assert players["player1"]["username"] == "player1"
        assert players["player1"]["overall"]["level"] == 1500
        assert players["player1"]["error"] is None

        # Players without data
        assert players["player2"]["error"] == "No data available"
        assert players["nonexistent"]["error"] == "No data available"

        # Check metadata
        metadata = data["metadata"]
        assert metadata["total_requested"] == 3
        assert metadata["total_found"] == 1
        assert metadata["total_missing"] == 2

        # Verify service was called correctly
        mock_statistics_service.get_multiple_stats.assert_called_once_with(
            ["player1", "player2", "nonexistent"]
        )
        mock_statistics_service.format_multiple_stats_response.assert_called_once_with(
            stats_map
        )

    def test_get_multiple_player_stats_empty_list(
        self, client, mock_statistics_service
    ):
        """Test getting stats with empty usernames list."""
        response = client.get(
            "/players/stats", headers={"Authorization": "Bearer fake_token"}
        )

        assert response.status_code == 422  # Validation error - min_items=1

    def test_get_multiple_player_stats_too_many_usernames(
        self, client, mock_statistics_service
    ):
        """Test getting stats with too many usernames."""
        # Create 51 usernames (exceeds limit of 50)
        usernames = [f"player{i}" for i in range(51)]
        query_params = "&".join(
            [f"usernames={username}" for username in usernames]
        )

        response = client.get(
            f"/players/stats?{query_params}",
            headers={"Authorization": "Bearer fake_token"},
        )

        assert response.status_code == 400
        assert "Maximum 50 usernames allowed" in response.json()["detail"]

    def test_get_multiple_player_stats_service_error(
        self, client, mock_statistics_service
    ):
        """Test handling of statistics service errors in multiple stats endpoint."""
        mock_statistics_service.get_multiple_stats.side_effect = (
            StatisticsServiceError("Database connection failed")
        )

        response = client.get(
            "/players/stats?usernames=player1",
            headers={"Authorization": "Bearer fake_token"},
        )

        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]

    def test_get_multiple_player_stats_duplicate_usernames(
        self, client, mock_statistics_service
    ):
        """Test getting stats with duplicate usernames (should be deduplicated)."""
        # Mock service responses
        stats_map = {"player1": None}
        mock_statistics_service.get_multiple_stats.return_value = stats_map
        mock_statistics_service.format_multiple_stats_response.return_value = {
            "players": {
                "player1": {
                    "username": "player1",
                    "fetched_at": None,
                    "overall": None,
                    "combat_level": None,
                    "skills": {},
                    "bosses": {},
                    "metadata": {
                        "total_skills": 0,
                        "total_bosses": 0,
                        "record_id": None,
                    },
                    "error": "No data available",
                },
            },
            "metadata": {
                "total_requested": 1,
                "total_found": 0,
                "total_missing": 1,
            },
        }

        response = client.get(
            "/players/stats?usernames=player1&usernames=player1&usernames=player1",
            headers={"Authorization": "Bearer fake_token"},
        )

        assert response.status_code == 200

        # Verify service was called with deduplicated list
        mock_statistics_service.get_multiple_stats.assert_called_once_with(
            ["player1"]
        )

    def test_authentication_required_single_player(
        self, client, mock_statistics_service
    ):
        """Test that authentication is required for single player stats endpoint."""
        # Remove auth override to test without authentication
        app = client.app
        del app.dependency_overrides[require_auth]

        response = client.get("/players/test_player/stats")

        # Without auth, FastAPI should return 401 for missing dependency
        assert response.status_code == 401

    def test_authentication_required_multiple_players(
        self, client, mock_statistics_service
    ):
        """Test that authentication is required for multiple players stats endpoint."""
        # Remove auth override to test without authentication
        app = client.app
        del app.dependency_overrides[require_auth]

        response = client.get("/players/stats?usernames=player1")

        # Without auth, FastAPI should return 401 for missing dependency
        assert response.status_code == 401

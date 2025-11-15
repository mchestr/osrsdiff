"""Tests for statistics service."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.exceptions import InvalidUsernameError
from app.models.hiscore import HiscoreRecord
from app.models.player import Player
from app.services.statistics import (
    NoDataAvailableError,
    PlayerNotFoundError,
    StatisticsService,
    StatisticsServiceError,
)


class TestStatisticsService:
    """Test cases for StatisticsService."""

    @pytest.fixture
    def statistics_service(self, test_session):
        """Create a statistics service instance for testing."""
        return StatisticsService(test_session)

    @pytest.fixture
    async def test_player(self, test_session):
        """Create a test player."""
        player = Player(username="testplayer")
        test_session.add(player)
        await test_session.commit()
        await test_session.refresh(player)
        return player

    @pytest.fixture
    async def test_player_with_stats(self, test_session):
        """Create a test player with hiscore records."""
        player = Player(username="playerWithSt")
        test_session.add(player)
        await test_session.flush()

        # Create sample hiscore records
        record1 = HiscoreRecord(
            player_id=player.id,
            fetched_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            overall_rank=1000,
            overall_level=1500,
            overall_experience=50000000,
            skills_data={
                "attack": {"rank": 500, "level": 99, "experience": 13034431},
                "defence": {"rank": 600, "level": 90, "experience": 5346332},
                "strength": {"rank": 400, "level": 99, "experience": 13034431},
                "hitpoints": {
                    "rank": 300,
                    "level": 99,
                    "experience": 13034431,
                },
                "prayer": {"rank": 800, "level": 70, "experience": 737627},
                "ranged": {"rank": 200, "level": 99, "experience": 13034431},
                "magic": {"rank": 100, "level": 99, "experience": 13034431},
            },
            bosses_data={
                "zulrah": {"rank": 1000, "kc": 500},
                "vorkath": {"rank": 2000, "kc": 200},
            },
        )

        record2 = HiscoreRecord(
            player_id=player.id,
            fetched_at=datetime(2024, 1, 2, 12, 0, 0, tzinfo=timezone.utc),
            overall_rank=950,
            overall_level=1520,
            overall_experience=52000000,
            skills_data={
                "attack": {"rank": 500, "level": 99, "experience": 13034431},
                "defence": {"rank": 580, "level": 91, "experience": 5902831},
                "strength": {"rank": 400, "level": 99, "experience": 13034431},
                "hitpoints": {
                    "rank": 300,
                    "level": 99,
                    "experience": 13034431,
                },
                "prayer": {"rank": 800, "level": 70, "experience": 737627},
                "ranged": {"rank": 200, "level": 99, "experience": 13034431},
                "magic": {"rank": 100, "level": 99, "experience": 13034431},
            },
            bosses_data={
                "zulrah": {"rank": 980, "kc": 520},
                "vorkath": {"rank": 1950, "kc": 210},
            },
        )

        test_session.add_all([record1, record2])
        await test_session.commit()
        await test_session.refresh(player)
        return player

    @pytest.mark.asyncio
    async def test_get_current_stats_success(
        self, statistics_service, test_player_with_stats
    ):
        """Test successfully getting current stats for a player."""
        result = await statistics_service.get_current_stats("playerWithSt")

        assert result is not None
        assert isinstance(result, HiscoreRecord)
        assert result.player.username == "playerWithSt"
        # Should return the most recent record (2024-01-02)
        assert result.fetched_at.day == 2
        assert result.overall_rank == 950
        assert result.overall_level == 1520

    @pytest.mark.asyncio
    async def test_get_current_stats_player_not_found(
        self, statistics_service
    ):
        """Test getting stats for non-existent player."""
        with pytest.raises(
            PlayerNotFoundError, match="Player 'nonexistent' not found"
        ):
            await statistics_service.get_current_stats("nonexistent")

    @pytest.mark.asyncio
    async def test_get_current_stats_empty_username(self, statistics_service):
        """Test getting stats with empty username."""
        with pytest.raises(
            InvalidUsernameError, match="Username cannot be empty"
        ):
            await statistics_service.get_current_stats("")

    @pytest.mark.asyncio
    async def test_get_current_stats_no_data(
        self, statistics_service, test_player
    ):
        """Test getting stats for player with no hiscore records."""
        result = await statistics_service.get_current_stats("testplayer")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_current_stats_case_insensitive(
        self, statistics_service, test_player_with_stats
    ):
        """Test getting stats with different case."""
        result = await statistics_service.get_current_stats("PLAYERWITHST")
        assert result is not None
        assert result.player.username == "playerWithSt"

    @pytest.mark.asyncio
    async def test_get_stats_at_date_success(
        self, statistics_service, test_player_with_stats
    ):
        """Test getting stats at a specific date."""
        # Get stats at 2024-01-01 15:00 (should return first record)
        target_date = datetime(2024, 1, 1, 15, 0, 0, tzinfo=timezone.utc)
        result = await statistics_service.get_stats_at_date(
            "playerWithSt", target_date
        )

        assert result is not None
        assert result.fetched_at.day == 1
        assert result.overall_rank == 1000

        # Get stats at 2024-01-02 15:00 (should return second record)
        target_date = datetime(2024, 1, 2, 15, 0, 0, tzinfo=timezone.utc)
        result = await statistics_service.get_stats_at_date(
            "playerWithSt", target_date
        )

        assert result is not None
        assert result.fetched_at.day == 2
        assert result.overall_rank == 950

    @pytest.mark.asyncio
    async def test_get_stats_at_date_before_any_records(
        self, statistics_service, test_player_with_stats
    ):
        """Test getting stats at date before any records exist."""
        target_date = datetime(2023, 12, 31, 12, 0, 0, tzinfo=timezone.utc)
        result = await statistics_service.get_stats_at_date(
            "playerWithSt", target_date
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_get_stats_at_date_player_not_found(
        self, statistics_service
    ):
        """Test getting stats at date for non-existent player."""
        target_date = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        with pytest.raises(
            PlayerNotFoundError, match="Player 'nonexistent' not found"
        ):
            await statistics_service.get_stats_at_date(
                "nonexistent", target_date
            )

    @pytest.mark.asyncio
    async def test_format_stats_response_success(
        self, statistics_service, test_player_with_stats
    ):
        """Test formatting a stats response."""
        record = await statistics_service.get_current_stats("playerWithSt")
        result = await statistics_service.format_stats_response(
            record, "playerWithSt"
        )

        assert "username" in result
        assert result["username"] == "playerWithSt"
        assert "fetched_at" in result
        assert "overall" in result
        assert "combat_level" in result
        assert "skills" in result
        assert "bosses" in result
        assert "metadata" in result

        # Check overall stats
        overall = result["overall"]
        assert overall["rank"] == 950
        assert overall["level"] == 1520
        assert overall["experience"] == 52000000

        # Check combat level calculation
        assert (
            result["combat_level"] == 120
        )  # Should calculate to 133 with these stats

        # Check skills data
        assert "attack" in result["skills"]
        assert result["skills"]["attack"]["level"] == 99

        # Check bosses data
        assert "zulrah" in result["bosses"]
        assert result["bosses"]["zulrah"]["kc"] == 520

        # Check metadata
        metadata = result["metadata"]
        assert metadata["total_skills"] == 7
        assert metadata["total_bosses"] == 2
        assert metadata["record_id"] == record.id

    @pytest.mark.asyncio
    async def test_format_stats_response_empty_record(
        self, statistics_service
    ):
        """Test formatting response for empty record."""
        result = await statistics_service.format_stats_response(
            None, "test_user"
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_username_normalization(
        self, statistics_service, test_player_with_stats
    ):
        """Test that usernames are properly normalized (trimmed)."""
        username_with_spaces = "  playerWithSt  "
        result = await statistics_service.get_current_stats(
            username_with_spaces
        )
        assert result is not None
        assert result.player.username == "playerWithSt"

    @pytest.mark.asyncio
    async def test_get_current_stats_with_relationship_loading(
        self, statistics_service, test_player_with_stats
    ):
        """Test that player relationship is properly loaded."""
        result = await statistics_service.get_current_stats("playerWithSt")
        assert result is not None
        assert result.player is not None
        assert result.player.username == "playerWithSt"
        # Should be able to access player attributes without additional queries
        assert result.player.is_active is True

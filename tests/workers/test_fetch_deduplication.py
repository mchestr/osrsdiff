"""Tests for hiscore data deduplication in fetch workers."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from src.models.hiscore import HiscoreRecord
from src.models.player import Player
from src.services.osrs_api import HiscoreData
from src.workers.fetch import _fetch_player_hiscores, _hiscore_data_changed


@pytest_asyncio.fixture
async def sample_player(test_session):
    """Create a sample player for testing."""
    player = Player(
        username="testplayer",
        is_active=True,
        fetch_interval_minutes=60,
    )
    test_session.add(player)
    await test_session.commit()
    await test_session.refresh(player)
    return player


class TestHiscoreDataDeduplication:
    """Test hiscore data deduplication logic."""

    def test_hiscore_data_changed_no_previous_record(self):
        """Test that data is considered changed when no previous record exists."""
        new_data = HiscoreData(
            overall={"rank": 1000, "level": 1500, "experience": 50000000},
            skills={
                "attack": {"rank": 500, "level": 99, "experience": 13034431}
            },
            bosses={"zulrah": {"rank": 100, "kc": 500}},
        )

        result = _hiscore_data_changed(new_data, None)
        assert result is True

    def test_hiscore_data_changed_overall_stats_different(self):
        """Test that data is considered changed when overall stats differ."""
        new_data = HiscoreData(
            overall={"rank": 1000, "level": 1500, "experience": 50000000},
            skills={
                "attack": {"rank": 500, "level": 99, "experience": 13034431}
            },
            bosses={"zulrah": {"rank": 100, "kc": 500}},
        )

        last_record = HiscoreRecord(
            overall_rank=1001,  # Different rank
            overall_level=1500,
            overall_experience=50000000,
            skills_data={
                "attack": {"rank": 500, "level": 99, "experience": 13034431}
            },
            bosses_data={"zulrah": {"rank": 100, "kc": 500}},
        )

        result = _hiscore_data_changed(new_data, last_record)
        assert result is True

    def test_hiscore_data_changed_skills_different(self):
        """Test that data is considered changed when skills data differs."""
        new_data = HiscoreData(
            overall={"rank": 1000, "level": 1500, "experience": 50000000},
            skills={
                "attack": {"rank": 500, "level": 99, "experience": 13034432}
            },  # Different XP
            bosses={"zulrah": {"rank": 100, "kc": 500}},
        )

        last_record = HiscoreRecord(
            overall_rank=1000,
            overall_level=1500,
            overall_experience=50000000,
            skills_data={
                "attack": {"rank": 500, "level": 99, "experience": 13034431}
            },
            bosses_data={"zulrah": {"rank": 100, "kc": 500}},
        )

        result = _hiscore_data_changed(new_data, last_record)
        assert result is True

    def test_hiscore_data_changed_bosses_different(self):
        """Test that data is considered changed when boss data differs."""
        new_data = HiscoreData(
            overall={"rank": 1000, "level": 1500, "experience": 50000000},
            skills={
                "attack": {"rank": 500, "level": 99, "experience": 13034431}
            },
            bosses={"zulrah": {"rank": 100, "kc": 501}},  # Different KC
        )

        last_record = HiscoreRecord(
            overall_rank=1000,
            overall_level=1500,
            overall_experience=50000000,
            skills_data={
                "attack": {"rank": 500, "level": 99, "experience": 13034431}
            },
            bosses_data={"zulrah": {"rank": 100, "kc": 500}},
        )

        result = _hiscore_data_changed(new_data, last_record)
        assert result is True

    def test_hiscore_data_unchanged(self):
        """Test that data is considered unchanged when all data matches."""
        new_data = HiscoreData(
            overall={"rank": 1000, "level": 1500, "experience": 50000000},
            skills={
                "attack": {"rank": 500, "level": 99, "experience": 13034431}
            },
            bosses={"zulrah": {"rank": 100, "kc": 500}},
        )

        last_record = HiscoreRecord(
            overall_rank=1000,
            overall_level=1500,
            overall_experience=50000000,
            skills_data={
                "attack": {"rank": 500, "level": 99, "experience": 13034431}
            },
            bosses_data={"zulrah": {"rank": 100, "kc": 500}},
        )

        result = _hiscore_data_changed(new_data, last_record)
        assert result is False

    def test_hiscore_data_unchanged_with_none_values(self):
        """Test that data comparison handles None values correctly."""
        new_data = HiscoreData(
            overall={"rank": None, "level": 1500, "experience": 50000000},
            skills={
                "attack": {"rank": 500, "level": 99, "experience": 13034431}
            },
            bosses={"zulrah": {"rank": None, "kc": 500}},
        )

        last_record = HiscoreRecord(
            overall_rank=None,
            overall_level=1500,
            overall_experience=50000000,
            skills_data={
                "attack": {"rank": 500, "level": 99, "experience": 13034431}
            },
            bosses_data={"zulrah": {"rank": None, "kc": 500}},
        )

        result = _hiscore_data_changed(new_data, last_record)
        assert result is False


class TestFetchPlayerHiscoresDeduplication:
    """Test the full fetch player hiscores task with deduplication."""

    @pytest.mark.asyncio
    async def test_fetch_unchanged_data_returns_unchanged_status(
        self, test_session, sample_player
    ):
        """Test that fetching unchanged data returns unchanged status and doesn't create new record."""
        # Create an existing hiscore record
        existing_record = HiscoreRecord(
            player_id=sample_player.id,
            fetched_at=datetime.now(timezone.utc),
            overall_rank=1000,
            overall_level=1500,
            overall_experience=50000000,
            skills_data={
                "attack": {"rank": 500, "level": 99, "experience": 13034431}
            },
            bosses_data={"zulrah": {"rank": 100, "kc": 500}},
        )
        test_session.add(existing_record)
        await test_session.commit()

        # Mock the OSRS API to return the same data
        mock_hiscore_data = HiscoreData(
            overall={"rank": 1000, "level": 1500, "experience": 50000000},
            skills={
                "attack": {"rank": 500, "level": 99, "experience": 13034431}
            },
            bosses={"zulrah": {"rank": 100, "kc": 500}},
            fetched_at=datetime.now(timezone.utc),
        )

        with (
            patch("src.workers.fetch.OSRSAPIClient") as mock_client_class,
            patch("src.workers.fetch.AsyncSessionLocal") as mock_session_local,
        ):

            mock_client = AsyncMock()
            mock_client.fetch_player_hiscores.return_value = mock_hiscore_data
            mock_client_class.return_value.__aenter__.return_value = (
                mock_client
            )

            # Mock the session to use our test session
            mock_session_local.return_value.__aenter__.return_value = (
                test_session
            )

            result = await _fetch_player_hiscores(sample_player.username)

        # Verify the result indicates unchanged data
        assert result["status"] == "unchanged"
        assert result["username"] == sample_player.username
        assert result["player_id"] == sample_player.id
        assert (
            result["message"] == "Hiscore data unchanged from previous fetch"
        )
        assert result["last_record_id"] == existing_record.id
        assert "record_id" not in result  # No new record created

        # Verify no new record was created
        from sqlalchemy import func, select

        count_stmt = select(func.count(HiscoreRecord.id)).where(
            HiscoreRecord.player_id == sample_player.id
        )
        count_result = await test_session.execute(count_stmt)
        record_count = count_result.scalar()
        assert record_count == 1  # Still only the original record

    @pytest.mark.asyncio
    async def test_fetch_changed_data_creates_new_record(
        self, test_session, sample_player
    ):
        """Test that fetching changed data creates a new record."""
        # Create an existing hiscore record
        existing_record = HiscoreRecord(
            player_id=sample_player.id,
            fetched_at=datetime.now(timezone.utc),
            overall_rank=1000,
            overall_level=1500,
            overall_experience=50000000,
            skills_data={
                "attack": {"rank": 500, "level": 99, "experience": 13034431}
            },
            bosses_data={"zulrah": {"rank": 100, "kc": 500}},
        )
        test_session.add(existing_record)
        await test_session.commit()

        # Mock the OSRS API to return different data
        mock_hiscore_data = HiscoreData(
            overall={
                "rank": 999,
                "level": 1500,
                "experience": 50000000,
            },  # Different rank
            skills={
                "attack": {"rank": 500, "level": 99, "experience": 13034431}
            },
            bosses={"zulrah": {"rank": 100, "kc": 500}},
            fetched_at=datetime.now(timezone.utc),
        )

        with (
            patch("src.workers.fetch.OSRSAPIClient") as mock_client_class,
            patch("src.workers.fetch.AsyncSessionLocal") as mock_session_local,
        ):

            mock_client = AsyncMock()
            mock_client.fetch_player_hiscores.return_value = mock_hiscore_data
            mock_client_class.return_value.__aenter__.return_value = (
                mock_client
            )

            # Mock the session to use our test session
            mock_session_local.return_value.__aenter__.return_value = (
                test_session
            )

            result = await _fetch_player_hiscores(sample_player.username)

        # Verify the result indicates success with new data
        assert result["status"] == "success"
        assert result["username"] == sample_player.username
        assert result["player_id"] == sample_player.id
        assert result["data_changed"] is True
        assert "record_id" in result
        assert result["record_id"] != existing_record.id

        # Verify a new record was created
        from sqlalchemy import func, select

        count_stmt = select(func.count(HiscoreRecord.id)).where(
            HiscoreRecord.player_id == sample_player.id
        )
        count_result = await test_session.execute(count_stmt)
        record_count = count_result.scalar()
        assert record_count == 2  # Original + new record

    @pytest.mark.asyncio
    async def test_fetch_first_time_creates_record(
        self, test_session, sample_player
    ):
        """Test that fetching for the first time always creates a record."""
        # Mock the OSRS API to return data
        mock_hiscore_data = HiscoreData(
            overall={"rank": 1000, "level": 1500, "experience": 50000000},
            skills={
                "attack": {"rank": 500, "level": 99, "experience": 13034431}
            },
            bosses={"zulrah": {"rank": 100, "kc": 500}},
            fetched_at=datetime.now(timezone.utc),
        )

        with (
            patch("src.workers.fetch.OSRSAPIClient") as mock_client_class,
            patch("src.workers.fetch.AsyncSessionLocal") as mock_session_local,
        ):

            mock_client = AsyncMock()
            mock_client.fetch_player_hiscores.return_value = mock_hiscore_data
            mock_client_class.return_value.__aenter__.return_value = (
                mock_client
            )

            # Mock the session to use our test session
            mock_session_local.return_value.__aenter__.return_value = (
                test_session
            )

            result = await _fetch_player_hiscores(sample_player.username)

        # Verify the result indicates success
        assert result["status"] == "success"
        assert result["username"] == sample_player.username
        assert result["player_id"] == sample_player.id
        assert result["data_changed"] is True
        assert "record_id" in result

        # Verify a record was created
        from sqlalchemy import func, select

        count_stmt = select(func.count(HiscoreRecord.id)).where(
            HiscoreRecord.player_id == sample_player.id
        )
        count_result = await test_session.execute(count_stmt)
        record_count = count_result.scalar()
        assert record_count == 1

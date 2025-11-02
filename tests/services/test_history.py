"""Tests for history service."""

import pytest
from datetime import datetime, timezone, timedelta

from src.models.player import Player
from src.models.hiscore import HiscoreRecord
from src.services.history import (
    HistoryService,
    HistoryServiceError,
    PlayerNotFoundError,
    InsufficientDataError,
    ProgressAnalysis,
    SkillProgress,
    BossProgress,
)


class TestHistoryService:
    """Test cases for HistoryService."""

    @pytest.fixture
    def history_service(self, test_session):
        """Create a history service instance for testing."""
        return HistoryService(test_session)

    @pytest.fixture
    async def test_player_with_history(self, test_session):
        """Create a test player with multiple hiscore records for progress analysis."""
        player = Player(username="progressPlayer")
        test_session.add(player)
        await test_session.flush()

        # Create a series of hiscore records over time (recent dates)
        base_date = datetime.now(timezone.utc) - timedelta(days=4)

        records = []
        for i in range(5):
            # Progress over 5 days
            record_date = base_date + timedelta(days=i)

            # Simulate skill progression
            attack_exp = 13034431 + (i * 100000)  # 100k XP per day
            defence_exp = 5346332 + (i * 50000)  # 50k XP per day
            attack_level = 99 if attack_exp >= 13034431 else 98
            defence_level = 90 + (i // 2)  # Level up every 2 days

            # Simulate boss progression
            zulrah_kc = 500 + (i * 10)  # 10 kills per day
            vorkath_kc = 200 + (i * 5)  # 5 kills per day

            record = HiscoreRecord(
                player_id=player.id,
                fetched_at=record_date,
                overall_rank=1000 - (i * 10),  # Rank improves
                overall_level=1500 + (i * 5),  # Total level increases
                overall_experience=50000000 + (i * 150000),  # Overall XP increases
                skills_data={
                    "attack": {
                        "rank": 500 - i,
                        "level": attack_level,
                        "experience": attack_exp,
                    },
                    "defence": {
                        "rank": 600 - i,
                        "level": defence_level,
                        "experience": defence_exp,
                    },
                    "strength": {"rank": 400, "level": 99, "experience": 13034431},
                    "hitpoints": {"rank": 300, "level": 99, "experience": 13034431},
                    "prayer": {"rank": 800, "level": 70, "experience": 737627},
                    "ranged": {"rank": 200, "level": 99, "experience": 13034431},
                    "magic": {"rank": 100, "level": 99, "experience": 13034431},
                },
                bosses_data={
                    "zulrah": {"rank": 1000 - (i * 5), "kill_count": zulrah_kc},
                    "vorkath": {"rank": 2000 - (i * 3), "kill_count": vorkath_kc},
                },
            )
            records.append(record)

        test_session.add_all(records)
        await test_session.commit()
        await test_session.refresh(player)
        return player

    @pytest.mark.asyncio
    async def test_get_progress_between_dates_success(
        self, history_service, test_player_with_history
    ):
        """Test successfully calculating progress between dates."""
        # Use dates that align with our test data
        base_date = datetime.now(timezone.utc) - timedelta(days=4)
        start_date = base_date + timedelta(hours=1)  # After first record
        end_date = base_date + timedelta(days=4, hours=1)  # After last record

        result = await history_service.get_progress_between_dates(
            "progressPlayer", start_date, end_date
        )

        assert isinstance(result, ProgressAnalysis)
        assert result.username == "progressPlayer"
        assert result.start_date == start_date
        assert result.end_date == end_date
        assert result.days_elapsed == 4

        # Check experience gains
        exp_gains = result.experience_gained
        assert exp_gains["overall"] == 600000  # 4 days * 150k per day
        assert exp_gains["attack"] == 400000  # 4 days * 100k per day
        assert exp_gains["defence"] == 200000  # 4 days * 50k per day

        # Check level gains
        level_gains = result.levels_gained
        assert level_gains["overall"] == 20  # 4 days * 5 per day
        assert level_gains["defence"] == 2  # 90 -> 92

        # Check boss kills gained
        boss_gains = result.boss_kills_gained
        assert boss_gains["zulrah"] == 40  # 4 days * 10 per day
        assert boss_gains["vorkath"] == 20  # 4 days * 5 per day

        # Check daily rates
        daily_exp = result.daily_experience_rates
        assert daily_exp["overall"] == 150000.0
        assert daily_exp["attack"] == 100000.0

        daily_boss = result.daily_boss_rates
        assert daily_boss["zulrah"] == 10.0
        assert daily_boss["vorkath"] == 5.0

    @pytest.mark.asyncio
    async def test_get_progress_between_dates_player_not_found(self, history_service):
        """Test progress calculation for non-existent player."""
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 2, tzinfo=timezone.utc)

        with pytest.raises(PlayerNotFoundError, match="Player 'nonexistent' not found"):
            await history_service.get_progress_between_dates(
                "nonexistent", start_date, end_date
            )

    @pytest.mark.asyncio
    async def test_get_progress_between_dates_invalid_date_range(
        self, history_service, test_player_with_history
    ):
        """Test progress calculation with invalid date range."""
        now = datetime.now(timezone.utc)
        start_date = now
        end_date = now - timedelta(days=1)  # End before start

        with pytest.raises(
            HistoryServiceError, match="Start date must be before end date"
        ):
            await history_service.get_progress_between_dates(
                "progressPlayer", start_date, end_date
            )

    @pytest.mark.asyncio
    async def test_get_progress_between_dates_insufficient_data(
        self, history_service, test_player_with_history
    ):
        """Test progress calculation with insufficient data."""
        # Date range before any records exist
        start_date = datetime.now(timezone.utc) - timedelta(days=30)
        end_date = datetime.now(timezone.utc) - timedelta(days=29)

        with pytest.raises(
            InsufficientDataError, match="Insufficient data for progress analysis"
        ):
            await history_service.get_progress_between_dates(
                "progressPlayer", start_date, end_date
            )

    @pytest.mark.asyncio
    async def test_get_skill_progress_success(
        self, history_service, test_player_with_history
    ):
        """Test getting skill-specific progress."""
        result = await history_service.get_skill_progress("progressPlayer", "attack", 7)

        assert isinstance(result, SkillProgress)
        assert result.username == "progressPlayer"
        assert result.skill_name == "attack"
        assert result.days == 7
        assert len(result.records) == 5  # All records have attack data

        # Check progress calculations
        assert result.total_experience_gained == 400000  # 4 days * 100k per day
        assert result.levels_gained == 0  # Already at 99
        assert result.daily_experience_rate == 400000 / 7  # Total gain / days

    @pytest.mark.asyncio
    async def test_get_skill_progress_with_level_gains(
        self, history_service, test_player_with_history
    ):
        """Test skill progress with actual level gains."""
        result = await history_service.get_skill_progress(
            "progressPlayer", "defence", 7
        )

        assert result.skill_name == "defence"
        assert result.total_experience_gained == 200000  # 4 days * 50k per day
        assert result.levels_gained == 2  # 90 -> 92
        assert result.daily_experience_rate == 200000 / 7

    @pytest.mark.asyncio
    async def test_get_skill_progress_player_not_found(self, history_service):
        """Test skill progress for non-existent player."""
        with pytest.raises(PlayerNotFoundError, match="Player 'nonexistent' not found"):
            await history_service.get_skill_progress("nonexistent", "attack", 7)

    @pytest.mark.asyncio
    async def test_get_skill_progress_invalid_parameters(
        self, history_service, test_player_with_history
    ):
        """Test skill progress with invalid parameters."""
        # Empty skill name
        with pytest.raises(HistoryServiceError, match="Skill name cannot be empty"):
            await history_service.get_skill_progress("progressPlayer", "", 7)

        # Invalid days
        with pytest.raises(HistoryServiceError, match="Days must be positive"):
            await history_service.get_skill_progress("progressPlayer", "attack", 0)

    @pytest.mark.asyncio
    async def test_get_boss_progress_success(
        self, history_service, test_player_with_history
    ):
        """Test getting boss-specific progress."""
        result = await history_service.get_boss_progress("progressPlayer", "zulrah", 7)

        assert isinstance(result, BossProgress)
        assert result.username == "progressPlayer"
        assert result.boss_name == "zulrah"
        assert result.days == 7
        assert len(result.records) == 5  # All records have zulrah data

        # Check progress calculations
        assert result.total_kills_gained == 40  # 4 days * 10 per day
        assert result.daily_kill_rate == 40 / 7  # Total kills / days

    @pytest.mark.asyncio
    async def test_get_boss_progress_player_not_found(self, history_service):
        """Test boss progress for non-existent player."""
        with pytest.raises(PlayerNotFoundError, match="Player 'nonexistent' not found"):
            await history_service.get_boss_progress("nonexistent", "zulrah", 7)

    @pytest.mark.asyncio
    async def test_get_boss_progress_invalid_parameters(
        self, history_service, test_player_with_history
    ):
        """Test boss progress with invalid parameters."""
        # Empty boss name
        with pytest.raises(HistoryServiceError, match="Boss name cannot be empty"):
            await history_service.get_boss_progress("progressPlayer", "", 7)

        # Invalid days
        with pytest.raises(HistoryServiceError, match="Days must be positive"):
            await history_service.get_boss_progress("progressPlayer", "zulrah", -1)

    @pytest.mark.asyncio
    async def test_progress_analysis_to_dict(
        self, history_service, test_player_with_history
    ):
        """Test converting progress analysis to dictionary."""
        base_date = datetime.now(timezone.utc) - timedelta(days=4)
        start_date = base_date + timedelta(hours=1)  # After first record
        end_date = base_date + timedelta(days=2, hours=1)

        result = await history_service.get_progress_between_dates(
            "progressPlayer", start_date, end_date
        )

        data = result.to_dict()

        assert data["username"] == "progressPlayer"
        assert "period" in data
        assert "records" in data
        assert "progress" in data
        assert "rates" in data

        # Check period data
        period = data["period"]
        assert period["days_elapsed"] == 2
        assert period["start_date"] == start_date.isoformat()
        assert period["end_date"] == end_date.isoformat()

        # Check progress data
        progress = data["progress"]
        assert "experience_gained" in progress
        assert "levels_gained" in progress
        assert "boss_kills_gained" in progress

        # Check rates data
        rates = data["rates"]
        assert "daily_experience" in rates
        assert "daily_boss_kills" in rates

    @pytest.mark.asyncio
    async def test_skill_progress_to_dict(
        self, history_service, test_player_with_history
    ):
        """Test converting skill progress to dictionary."""
        result = await history_service.get_skill_progress("progressPlayer", "attack", 7)
        data = result.to_dict()

        assert data["username"] == "progressPlayer"
        assert data["skill"] == "attack"
        assert data["period_days"] == 7
        assert data["total_records"] == 5

        # Check progress data
        progress = data["progress"]
        assert "experience_gained" in progress
        assert "levels_gained" in progress
        assert "daily_experience_rate" in progress

        # Check timeline data
        timeline = data["timeline"]
        assert len(timeline) == 5
        assert all("date" in entry for entry in timeline)
        assert all("level" in entry for entry in timeline)
        assert all("experience" in entry for entry in timeline)

    @pytest.mark.asyncio
    async def test_boss_progress_to_dict(
        self, history_service, test_player_with_history
    ):
        """Test converting boss progress to dictionary."""
        result = await history_service.get_boss_progress("progressPlayer", "vorkath", 7)
        data = result.to_dict()

        assert data["username"] == "progressPlayer"
        assert data["boss"] == "vorkath"
        assert data["period_days"] == 7
        assert data["total_records"] == 5

        # Check progress data
        progress = data["progress"]
        assert "kills_gained" in progress
        assert "daily_kill_rate" in progress

        # Check timeline data
        timeline = data["timeline"]
        assert len(timeline) == 5
        assert all("date" in entry for entry in timeline)
        assert all("kill_count" in entry for entry in timeline)

    @pytest.mark.asyncio
    async def test_username_normalization(
        self, history_service, test_player_with_history
    ):
        """Test that usernames are properly normalized."""
        base_date = datetime.now(timezone.utc) - timedelta(days=4)
        start_date = base_date + timedelta(hours=1)  # After first record
        end_date = base_date + timedelta(days=1, hours=1)

        # Test with spaces around username
        result = await history_service.get_progress_between_dates(
            "  progressPlayer  ", start_date, end_date
        )
        assert result.username == "progressPlayer"

    @pytest.mark.asyncio
    async def test_case_insensitive_skill_and_boss_names(
        self, history_service, test_player_with_history
    ):
        """Test that skill and boss names are case insensitive."""
        # Test skill with different cases
        result1 = await history_service.get_skill_progress(
            "progressPlayer", "ATTACK", 7
        )
        result2 = await history_service.get_skill_progress(
            "progressPlayer", "Attack", 7
        )
        result3 = await history_service.get_skill_progress(
            "progressPlayer", "attack", 7
        )

        assert result1.skill_name == "attack"
        assert result2.skill_name == "attack"
        assert result3.skill_name == "attack"

        # Test boss with different cases
        boss1 = await history_service.get_boss_progress("progressPlayer", "ZULRAH", 7)
        boss2 = await history_service.get_boss_progress("progressPlayer", "Zulrah", 7)
        boss3 = await history_service.get_boss_progress("progressPlayer", "zulrah", 7)

        assert boss1.boss_name == "zulrah"
        assert boss2.boss_name == "zulrah"
        assert boss3.boss_name == "zulrah"

    @pytest.mark.asyncio
    async def test_empty_username_validation(self, history_service):
        """Test validation of empty usernames."""
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 2, tzinfo=timezone.utc)

        with pytest.raises(PlayerNotFoundError, match="Username cannot be empty"):
            await history_service.get_progress_between_dates("", start_date, end_date)

        with pytest.raises(PlayerNotFoundError, match="Username cannot be empty"):
            await history_service.get_skill_progress("", "attack", 7)

        with pytest.raises(PlayerNotFoundError, match="Username cannot be empty"):
            await history_service.get_boss_progress("", "zulrah", 7)

    @pytest.mark.asyncio
    async def test_progress_analysis_edge_cases(
        self, history_service, test_player_with_history
    ):
        """Test edge cases in progress analysis calculations."""
        # Test with same start and end record (should raise error)
        base_date = datetime.now(timezone.utc) - timedelta(days=4)
        start_date = base_date + timedelta(hours=12)  # Exact time of first record
        end_date = base_date + timedelta(hours=12, seconds=1)  # 1 second later

        with pytest.raises(
            InsufficientDataError, match="Start and end records are the same"
        ):
            await history_service.get_progress_between_dates(
                "progressPlayer", start_date, end_date
            )

    @pytest.mark.asyncio
    async def test_insufficient_skill_data(self, history_service, test_session):
        """Test skill progress with insufficient skill-specific data."""
        # Create player with records that don't have the requested skill
        player = Player(username="limitedPlayer")
        test_session.add(player)
        await test_session.flush()

        # Create records without 'cooking' skill data (recent dates)
        base_date = datetime.now(timezone.utc) - timedelta(days=2)
        record1 = HiscoreRecord(
            player_id=player.id,
            fetched_at=base_date,
            skills_data={"attack": {"rank": 500, "level": 99, "experience": 13034431}},
        )
        record2 = HiscoreRecord(
            player_id=player.id,
            fetched_at=base_date + timedelta(days=1),
            skills_data={"attack": {"rank": 500, "level": 99, "experience": 13034431}},
        )

        test_session.add_all([record1, record2])
        await test_session.commit()

        # Should raise error for skill not in data
        with pytest.raises(InsufficientDataError, match="Insufficient cooking data"):
            await history_service.get_skill_progress("limitedPlayer", "cooking", 7)

    @pytest.mark.asyncio
    async def test_insufficient_boss_data(self, history_service, test_session):
        """Test boss progress with insufficient boss-specific data."""
        # Create player with records that don't have the requested boss
        player = Player(username="limitedBossPlayer")
        test_session.add(player)
        await test_session.flush()

        # Create records without 'bandos' boss data (recent dates)
        base_date = datetime.now(timezone.utc) - timedelta(days=2)
        record1 = HiscoreRecord(
            player_id=player.id,
            fetched_at=base_date,
            bosses_data={"zulrah": {"rank": 1000, "kill_count": 500}},
        )
        record2 = HiscoreRecord(
            player_id=player.id,
            fetched_at=base_date + timedelta(days=1),
            bosses_data={"zulrah": {"rank": 1000, "kill_count": 500}},
        )

        test_session.add_all([record1, record2])
        await test_session.commit()

        # Should raise error for boss not in data
        with pytest.raises(InsufficientDataError, match="Insufficient bandos data"):
            await history_service.get_boss_progress("limitedBossPlayer", "bandos", 7)

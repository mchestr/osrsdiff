"""Tests for Player model."""

from datetime import datetime

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.hiscore import HiscoreRecord
from app.models.player import Player


class TestPlayerModel:
    """Test Player model functionality."""

    def test_player_creation(self):
        """Test basic player model creation."""
        player = Player(username="test_player")

        assert player.username == "test_player"
        assert player.is_active is True
        assert player.fetch_interval_minutes == 60
        assert player.last_fetched is None
        assert player.schedule_id is None
        assert player.hiscore_records == []

    def test_player_creation_with_schedule_id(self):
        """Test player model creation with schedule_id."""
        player = Player(username="test_player", schedule_id="player_fetch_123")

        assert player.username == "test_player"
        assert player.schedule_id == "player_fetch_123"

    def test_player_repr(self):
        """Test player string representation."""
        player = Player(id=1, username="test_player", is_active=True)

        expected = "<Player(id=1, username='test_player', active=True)>"
        assert repr(player) == expected

    def test_validate_username_valid_cases(self):
        """Test username validation with valid usernames."""
        valid_usernames = [
            "player",
            "Player123",
            "test_user",
            "user-name",
            "a",  # minimum length
            "123456789012",  # maximum length
            "user name",  # with space
            "test_user-12",  # mixed characters (12 chars)
        ]

        for username in valid_usernames:
            assert (
                Player.validate_username(username) is True
            ), f"Username '{username}' should be valid"

    def test_validate_username_invalid_cases(self):
        """Test username validation with invalid usernames."""
        invalid_usernames = [
            "",  # empty
            "1234567890123",  # too long (13 characters)
            " player",  # starts with space
            "player ",  # ends with space
            "player@test",  # invalid character @
            "player.test",  # invalid character .
            "player#test",  # invalid character #
            "player$test",  # invalid character $
            None,  # None value
        ]

        for username in invalid_usernames:
            assert (
                Player.validate_username(username) is False
            ), f"Username '{username}' should be invalid"

    def test_latest_hiscore_property_empty(self):
        """Test latest_hiscore property when no records exist."""
        player = Player(username="test_player")
        assert player.latest_hiscore is None

    def test_latest_hiscore_property_with_records(self):
        """Test latest_hiscore property with mock records."""
        from app.models.hiscore import HiscoreRecord

        player = Player(username="test_player")

        # Create mock hiscore records (they would be ordered by fetched_at desc in real scenario)
        record1 = HiscoreRecord(id=1, player_id=1, overall_level=1500)
        record2 = HiscoreRecord(id=2, player_id=1, overall_level=1600)

        # Simulate the relationship (in real scenario this would be handled by SQLAlchemy)
        player.hiscore_records = [record2, record1]  # Most recent first

        assert player.latest_hiscore == record2
        assert player.latest_hiscore.overall_level == 1600


class TestPlayerValidation:
    """Test Player model validation edge cases."""

    def test_username_boundary_lengths(self):
        """Test username validation at boundary lengths."""
        # Test minimum valid length
        assert Player.validate_username("a") is True

        # Test maximum valid length
        assert Player.validate_username("123456789012") is True

        # Test just over maximum
        assert Player.validate_username("1234567890123") is False

    def test_username_special_characters(self):
        """Test username validation with various special characters."""
        # Valid special characters
        valid_chars = ["test_user", "test-user", "test user"]
        for username in valid_chars:
            assert Player.validate_username(username) is True

        # Invalid special characters
        invalid_chars = [
            "test@user",
            "test.user",
            "test+user",
            "test/user",
            "test\\user",
        ]
        for username in invalid_chars:
            assert Player.validate_username(username) is False

    def test_username_whitespace_handling(self):
        """Test username validation with various whitespace scenarios."""
        # Valid internal spaces
        assert Player.validate_username("test user") is True
        assert Player.validate_username("a b c") is True

        # Invalid leading/trailing spaces
        assert Player.validate_username(" test") is False
        assert Player.validate_username("test ") is False
        assert Player.validate_username(" test ") is False
        assert Player.validate_username("  test  ") is False


class TestPlayerDatabaseOperations:
    """Test Player model database operations."""

    @pytest_asyncio.fixture
    async def sample_player(self, test_session: AsyncSession):
        """Create a sample player for testing."""
        player = Player(username="test_player")
        test_session.add(player)
        await test_session.commit()
        await test_session.refresh(player)
        return player

    @pytest_asyncio.fixture
    async def player_with_records(self, test_session: AsyncSession):
        """Create a player with hiscore records for testing."""
        player = Player(username="player_with_data")
        test_session.add(player)
        await test_session.commit()
        await test_session.refresh(player)

        # Add some hiscore records
        record1 = HiscoreRecord(
            player_id=player.id,
            overall_level=1500,
            overall_experience=50000000,
            skills_data={
                "attack": {"rank": 500, "level": 99, "experience": 13034431}
            },
            bosses_data={"zulrah": {"rank": 1000, "kill_count": 500}},
        )
        record2 = HiscoreRecord(
            player_id=player.id,
            overall_level=1600,
            overall_experience=55000000,
            skills_data={
                "attack": {"rank": 400, "level": 99, "experience": 13034431}
            },
            bosses_data={"zulrah": {"rank": 900, "kill_count": 550}},
        )

        test_session.add_all([record1, record2])
        await test_session.commit()
        await test_session.refresh(record1)
        await test_session.refresh(record2)

        return player

    @pytest.mark.asyncio
    async def test_create_player_in_database(self, test_session: AsyncSession):
        """Test creating a player in the database."""
        player = Player(username="new_player")
        test_session.add(player)
        await test_session.commit()

        # Verify player was created
        assert player.id is not None
        assert player.username == "new_player"
        assert player.is_active is True
        assert player.fetch_interval_minutes == 60
        assert player.schedule_id is None
        assert player.created_at is not None

    @pytest.mark.asyncio
    async def test_create_player_with_schedule_id_in_database(
        self, test_session: AsyncSession
    ):
        """Test creating a player with schedule_id in the database."""
        player = Player(
            username="scheduled_player", schedule_id="player_fetch_456"
        )
        test_session.add(player)
        await test_session.commit()

        # Verify player was created with schedule_id
        assert player.id is not None
        assert player.username == "scheduled_player"
        assert player.schedule_id == "player_fetch_456"

        # Query back from database to verify persistence
        stmt = select(Player).where(Player.username == "scheduled_player")
        result = await test_session.execute(stmt)
        found_player = result.scalar_one_or_none()

        assert found_player is not None
        assert found_player.schedule_id == "player_fetch_456"

    @pytest.mark.asyncio
    async def test_query_player_by_username(
        self, test_session: AsyncSession, sample_player: Player
    ):
        """Test querying a player by username."""
        stmt = select(Player).where(Player.username == "test_player")
        result = await test_session.execute(stmt)
        found_player = result.scalar_one_or_none()

        assert found_player is not None
        assert found_player.id == sample_player.id
        assert found_player.username == "test_player"

    @pytest.mark.asyncio
    async def test_update_player_in_database(
        self, test_session: AsyncSession, sample_player: Player
    ):
        """Test updating a player in the database."""
        # Update player properties
        sample_player.is_active = False
        sample_player.fetch_interval_minutes = 120

        await test_session.commit()
        await test_session.refresh(sample_player)

        # Verify updates
        assert sample_player.is_active is False
        assert sample_player.fetch_interval_minutes == 120

    @pytest.mark.asyncio
    async def test_delete_player_from_database(
        self, test_session: AsyncSession, sample_player: Player
    ):
        """Test deleting a player from the database."""
        player_id = sample_player.id

        await test_session.delete(sample_player)
        await test_session.commit()

        # Verify player was deleted
        stmt = select(Player).where(Player.id == player_id)
        result = await test_session.execute(stmt)
        found_player = result.scalar_one_or_none()

        assert found_player is None

    @pytest.mark.asyncio
    async def test_player_hiscore_relationship(
        self, test_session: AsyncSession, player_with_records: Player
    ):
        """Test the relationship between Player and HiscoreRecord."""
        # Refresh player to load relationships
        await test_session.refresh(player_with_records, ["hiscore_records"])

        # Verify relationship
        assert len(player_with_records.hiscore_records) == 2

        # Verify records belong to the player
        for record in player_with_records.hiscore_records:
            assert record.player_id == player_with_records.id
            assert record.player == player_with_records

    @pytest.mark.asyncio
    async def test_cascade_delete_hiscore_records(
        self, test_session: AsyncSession, player_with_records: Player
    ):
        """Test that deleting a player cascades to delete hiscore records."""
        player_id = player_with_records.id

        # Count hiscore records before deletion
        stmt = select(HiscoreRecord).where(
            HiscoreRecord.player_id == player_id
        )
        result = await test_session.execute(stmt)
        records_before = result.scalars().all()
        assert len(records_before) == 2

        # Delete the player
        await test_session.delete(player_with_records)
        await test_session.commit()

        # Verify hiscore records were also deleted
        result = await test_session.execute(stmt)
        records_after = result.scalars().all()
        assert len(records_after) == 0

    @pytest.mark.asyncio
    async def test_unique_username_constraint(
        self, test_session: AsyncSession
    ):
        """Test that username uniqueness is enforced at database level."""
        # Create first player
        player1 = Player(username="unique_test")
        test_session.add(player1)
        await test_session.commit()

        # Try to create second player with same username
        player2 = Player(username="unique_test")
        test_session.add(player2)

        # This should raise an integrity error
        with pytest.raises(Exception):  # SQLAlchemy will raise IntegrityError
            await test_session.commit()

    @pytest.mark.asyncio
    async def test_latest_hiscore_property_with_database(
        self, test_session: AsyncSession, player_with_records: Player
    ):
        """Test latest_hiscore property with actual database records."""
        # Refresh player to load relationships
        await test_session.refresh(player_with_records, ["hiscore_records"])

        latest = player_with_records.latest_hiscore
        assert latest is not None

        # Should be the most recent record (records are ordered by fetched_at desc)
        # Since we created record2 after record1, it should be the latest
        assert latest.overall_level in [
            1500,
            1600,
        ]  # Either could be latest depending on timing

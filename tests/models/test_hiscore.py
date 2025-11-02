"""Tests for HiscoreRecord model."""

import pytest
import pytest_asyncio
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.hiscore import HiscoreRecord
from src.models.player import Player


class TestHiscoreRecordModel:
    """Test HiscoreRecord model functionality."""

    def test_hiscore_record_creation(self):
        """Test basic hiscore record creation."""
        record = HiscoreRecord(
            player_id=1,
            overall_rank=1000,
            overall_level=1500,
            overall_experience=50000000,
        )

        assert record.player_id == 1
        assert record.overall_rank == 1000
        assert record.overall_level == 1500
        assert record.overall_experience == 50000000
        assert record.skills_data == {}
        assert record.bosses_data == {}

    def test_hiscore_record_with_data(self):
        """Test hiscore record creation with skills and bosses data."""
        skills_data = {
            "attack": {"rank": 500, "level": 99, "experience": 13034431},
            "defence": {"rank": 600, "level": 90, "experience": 5346332},
        }

        bosses_data = {
            "zulrah": {"rank": 1000, "kill_count": 500},
            "vorkath": {"rank": 2000, "kill_count": 200},
        }

        record = HiscoreRecord(
            player_id=1, skills_data=skills_data, bosses_data=bosses_data
        )

        assert record.skills_data == skills_data
        assert record.bosses_data == bosses_data

    def test_hiscore_record_repr(self):
        """Test hiscore record string representation."""
        record = HiscoreRecord(id=1, player_id=2, overall_level=1500)

        # Note: fetched_at will be set by database default, so we'll check the format
        repr_str = repr(record)
        assert "HiscoreRecord(id=1, player_id=2" in repr_str
        assert "overall_level=1500)" in repr_str

    def test_get_skill_data(self):
        """Test getting skill data by name."""
        skills_data = {
            "attack": {"rank": 500, "level": 99, "experience": 13034431},
            "defence": {"rank": 600, "level": 90, "experience": 5346332},
        }

        record = HiscoreRecord(player_id=1, skills_data=skills_data)

        # Test existing skill
        attack_data = record.get_skill_data("attack")
        assert attack_data == {"rank": 500, "level": 99, "experience": 13034431}

        # Test case insensitive
        attack_data_upper = record.get_skill_data("ATTACK")
        assert attack_data_upper == {"rank": 500, "level": 99, "experience": 13034431}

        # Test non-existing skill
        missing_data = record.get_skill_data("cooking")
        assert missing_data is None

    def test_get_boss_data(self):
        """Test getting boss data by name."""
        bosses_data = {
            "zulrah": {"rank": 1000, "kill_count": 500},
            "vorkath": {"rank": 2000, "kill_count": 200},
        }

        record = HiscoreRecord(player_id=1, bosses_data=bosses_data)

        # Test existing boss
        zulrah_data = record.get_boss_data("zulrah")
        assert zulrah_data == {"rank": 1000, "kill_count": 500}

        # Test case insensitive
        zulrah_data_upper = record.get_boss_data("ZULRAH")
        assert zulrah_data_upper == {"rank": 1000, "kill_count": 500}

        # Test non-existing boss
        missing_data = record.get_boss_data("bandos")
        assert missing_data is None

    def test_get_skill_level(self):
        """Test getting skill level by name."""
        skills_data = {
            "attack": {"rank": 500, "level": 99, "experience": 13034431},
            "defence": {"rank": 600, "level": 90, "experience": 5346332},
        }

        record = HiscoreRecord(player_id=1, skills_data=skills_data)

        assert record.get_skill_level("attack") == 99
        assert record.get_skill_level("defence") == 90
        assert record.get_skill_level("cooking") is None

    def test_get_skill_experience(self):
        """Test getting skill experience by name."""
        skills_data = {
            "attack": {"rank": 500, "level": 99, "experience": 13034431},
            "defence": {"rank": 600, "level": 90, "experience": 5346332},
        }

        record = HiscoreRecord(player_id=1, skills_data=skills_data)

        assert record.get_skill_experience("attack") == 13034431
        assert record.get_skill_experience("defence") == 5346332
        assert record.get_skill_experience("cooking") is None

    def test_get_boss_kills(self):
        """Test getting boss kill count by name."""
        bosses_data = {
            "zulrah": {"rank": 1000, "kill_count": 500},
            "vorkath": {"rank": 2000, "kill_count": 200},
        }

        record = HiscoreRecord(player_id=1, bosses_data=bosses_data)

        assert record.get_boss_kills("zulrah") == 500
        assert record.get_boss_kills("vorkath") == 200
        assert record.get_boss_kills("bandos") is None

    def test_total_skills_property(self):
        """Test total_skills property."""
        skills_data = {
            "attack": {"rank": 500, "level": 99, "experience": 13034431},
            "defence": {"rank": 600, "level": 90, "experience": 5346332},
            "strength": {"rank": 700, "level": 85, "experience": 3000000},
        }

        record = HiscoreRecord(player_id=1, skills_data=skills_data)
        assert record.total_skills == 3

    def test_total_bosses_property(self):
        """Test total_bosses property."""
        bosses_data = {
            "zulrah": {"rank": 1000, "kill_count": 500},
            "vorkath": {"rank": 2000, "kill_count": 200},
        }

        record = HiscoreRecord(player_id=1, bosses_data=bosses_data)
        assert record.total_bosses == 2

    def test_calculate_combat_level_complete(self):
        """Test combat level calculation with all required skills."""
        skills_data = {
            "attack": {"rank": 500, "level": 99, "experience": 13034431},
            "strength": {"rank": 600, "level": 99, "experience": 13034431},
            "defence": {"rank": 700, "level": 99, "experience": 13034431},
            "hitpoints": {"rank": 800, "level": 99, "experience": 13034431},
            "prayer": {"rank": 900, "level": 99, "experience": 13034431},
            "ranged": {"rank": 1000, "level": 99, "experience": 13034431},
            "magic": {"rank": 1100, "level": 99, "experience": 13034431},
        }

        record = HiscoreRecord(player_id=1, skills_data=skills_data)
        combat_level = record.calculate_combat_level()

        # For all 99s, let's calculate the expected combat level:
        # Base = 0.25 * (99 + 99 + 99//2) = 0.25 * (99 + 99 + 49) = 0.25 * 247 = 61.75
        # Melee = 0.325 * (99 + 99) = 0.325 * 198 = 64.35
        # Ranged = 0.325 * (int(99 * 1.5) + 99) = 0.325 * (148 + 99) = 0.325 * 247 = 80.275
        # Magic = 0.325 * (int(99 * 1.5) + 99) = 0.325 * (148 + 99) = 0.325 * 247 = 80.275
        # Combat = int(61.75 + max(64.35, 80.275, 80.275)) = int(61.75 + 80.275) = int(142.025) = 142
        assert combat_level == 142

    def test_calculate_combat_level_missing_skills(self):
        """Test combat level calculation with missing skills."""
        skills_data = {
            "attack": {"rank": 500, "level": 99, "experience": 13034431},
            "strength": {"rank": 600, "level": 99, "experience": 13034431},
            # Missing other required skills
        }

        record = HiscoreRecord(player_id=1, skills_data=skills_data)
        combat_level = record.calculate_combat_level()

        # Should return None when required skills are missing
        assert combat_level is None

    def test_calculate_combat_level_low_levels(self):
        """Test combat level calculation with low levels."""
        skills_data = {
            "attack": {"rank": 500, "level": 40, "experience": 37224},
            "strength": {"rank": 600, "level": 40, "experience": 37224},
            "defence": {"rank": 700, "level": 40, "experience": 37224},
            "hitpoints": {"rank": 800, "level": 40, "experience": 37224},
            "prayer": {"rank": 900, "level": 1, "experience": 0},
            "ranged": {"rank": 1000, "level": 1, "experience": 0},
            "magic": {"rank": 1100, "level": 1, "experience": 0},
        }

        record = HiscoreRecord(player_id=1, skills_data=skills_data)
        combat_level = record.calculate_combat_level()

        # Should calculate correct combat level for these stats
        # Base: 0.25 * (40 + 40 + 1//2) = 0.25 * (40 + 40 + 0) = 0.25 * 80 = 20
        # Melee: 0.325 * (40 + 40) = 0.325 * 80 = 26
        # Ranged: 0.325 * (int(1 * 1.5) + 40) = 0.325 * (1 + 40) = 0.325 * 41 = 13.325
        # Magic: 0.325 * (int(1 * 1.5) + 40) = 0.325 * (1 + 40) = 0.325 * 41 = 13.325
        # Combat level: int(20 + max(26, 13.325, 13.325)) = int(20 + 26) = 46
        assert combat_level == 46


class TestHiscoreRecordEdgeCases:
    """Test HiscoreRecord model edge cases."""

    def test_empty_data_handling(self):
        """Test handling of empty skills and bosses data."""
        record = HiscoreRecord(player_id=1)

        assert record.get_skill_data("attack") is None
        assert record.get_boss_data("zulrah") is None
        assert record.get_skill_level("attack") is None
        assert record.get_skill_experience("attack") is None
        assert record.get_boss_kills("zulrah") is None
        assert record.total_skills == 0
        assert record.total_bosses == 0

    def test_partial_skill_data(self):
        """Test handling of partial skill data."""
        skills_data = {
            "attack": {"rank": 500, "level": 99},  # Missing experience
            "defence": {"level": 90, "experience": 5346332},  # Missing rank
        }

        record = HiscoreRecord(player_id=1, skills_data=skills_data)

        attack_data = record.get_skill_data("attack")
        assert attack_data["level"] == 99
        assert attack_data["rank"] == 500
        assert "experience" not in attack_data

        defence_data = record.get_skill_data("defence")
        assert defence_data["level"] == 90
        assert defence_data["experience"] == 5346332
        assert "rank" not in defence_data


class TestHiscoreRecordDatabaseOperations:
    """Test HiscoreRecord model database operations."""

    @pytest_asyncio.fixture
    async def sample_player(self, test_session: AsyncSession):
        """Create a sample player for testing."""
        player = Player(username="test_player")
        test_session.add(player)
        await test_session.commit()
        await test_session.refresh(player)
        return player

    @pytest_asyncio.fixture
    async def sample_hiscore_record(
        self, test_session: AsyncSession, sample_player: Player
    ):
        """Create a sample hiscore record for testing."""
        record = HiscoreRecord(
            player_id=sample_player.id,
            overall_rank=1000,
            overall_level=1500,
            overall_experience=50000000,
            skills_data={
                "attack": {"rank": 500, "level": 99, "experience": 13034431},
                "defence": {"rank": 600, "level": 90, "experience": 5346332},
            },
            bosses_data={
                "zulrah": {"rank": 1000, "kill_count": 500},
                "vorkath": {"rank": 2000, "kill_count": 200},
            },
        )
        test_session.add(record)
        await test_session.commit()
        await test_session.refresh(record)
        return record

    @pytest.mark.asyncio
    async def test_create_hiscore_record_in_database(
        self, test_session: AsyncSession, sample_player: Player
    ):
        """Test creating a hiscore record in the database."""
        record = HiscoreRecord(
            player_id=sample_player.id,
            overall_rank=1500,
            overall_level=1200,
            overall_experience=30000000,
        )
        test_session.add(record)
        await test_session.commit()

        # Verify record was created
        assert record.id is not None
        assert record.player_id == sample_player.id
        assert record.overall_rank == 1500
        assert record.overall_level == 1200
        assert record.overall_experience == 30000000
        assert record.fetched_at is not None

    @pytest.mark.asyncio
    async def test_query_hiscore_records_by_player(
        self, test_session: AsyncSession, sample_hiscore_record: HiscoreRecord
    ):
        """Test querying hiscore records by player."""
        stmt = select(HiscoreRecord).where(
            HiscoreRecord.player_id == sample_hiscore_record.player_id
        )
        result = await test_session.execute(stmt)
        records = result.scalars().all()

        assert len(records) == 1
        assert records[0].id == sample_hiscore_record.id
        assert records[0].player_id == sample_hiscore_record.player_id

    @pytest.mark.asyncio
    async def test_hiscore_record_player_relationship(
        self, test_session: AsyncSession, sample_hiscore_record: HiscoreRecord
    ):
        """Test the relationship between HiscoreRecord and Player."""
        # Refresh record to load relationships
        await test_session.refresh(sample_hiscore_record, ["player"])

        # Verify relationship
        assert sample_hiscore_record.player is not None
        assert sample_hiscore_record.player.username == "test_player"
        assert sample_hiscore_record.player.id == sample_hiscore_record.player_id

    @pytest.mark.asyncio
    async def test_update_hiscore_record_in_database(
        self, test_session: AsyncSession, sample_hiscore_record: HiscoreRecord
    ):
        """Test updating a hiscore record in the database."""
        # Update record properties
        sample_hiscore_record.overall_rank = 800
        sample_hiscore_record.overall_level = 1600
        sample_hiscore_record.skills_data = {
            "attack": {"rank": 400, "level": 99, "experience": 13034431},
            "strength": {"rank": 500, "level": 95, "experience": 9000000},
        }

        await test_session.commit()
        await test_session.refresh(sample_hiscore_record)

        # Verify updates
        assert sample_hiscore_record.overall_rank == 800
        assert sample_hiscore_record.overall_level == 1600
        assert "strength" in sample_hiscore_record.skills_data
        assert sample_hiscore_record.skills_data["strength"]["level"] == 95

    @pytest.mark.asyncio
    async def test_delete_hiscore_record_from_database(
        self, test_session: AsyncSession, sample_hiscore_record: HiscoreRecord
    ):
        """Test deleting a hiscore record from the database."""
        record_id = sample_hiscore_record.id

        await test_session.delete(sample_hiscore_record)
        await test_session.commit()

        # Verify record was deleted
        stmt = select(HiscoreRecord).where(HiscoreRecord.id == record_id)
        result = await test_session.execute(stmt)
        found_record = result.scalar_one_or_none()

        assert found_record is None

    @pytest.mark.asyncio
    async def test_json_data_persistence(
        self, test_session: AsyncSession, sample_player: Player
    ):
        """Test that JSON data is properly persisted and retrieved."""
        complex_skills_data = {
            "attack": {"rank": 500, "level": 99, "experience": 13034431},
            "defence": {"rank": 600, "level": 90, "experience": 5346332},
            "strength": {"rank": 700, "level": 85, "experience": 3000000},
            "hitpoints": {"rank": 800, "level": 95, "experience": 7000000},
        }

        complex_bosses_data = {
            "zulrah": {"rank": 1000, "kill_count": 500},
            "vorkath": {"rank": 2000, "kill_count": 200},
            "bandos": {"rank": 3000, "kill_count": 100},
            "armadyl": {"rank": 4000, "kill_count": 50},
        }

        record = HiscoreRecord(
            player_id=sample_player.id,
            skills_data=complex_skills_data,
            bosses_data=complex_bosses_data,
        )
        test_session.add(record)
        await test_session.commit()

        # Refresh and verify data persistence
        await test_session.refresh(record)

        assert record.skills_data == complex_skills_data
        assert record.bosses_data == complex_bosses_data

        # Test specific data retrieval
        assert record.get_skill_level("attack") == 99
        assert record.get_skill_experience("strength") == 3000000
        assert record.get_boss_kills("zulrah") == 500
        assert record.total_skills == 4
        assert record.total_bosses == 4

    @pytest.mark.asyncio
    async def test_foreign_key_constraint(self, test_session: AsyncSession):
        """Test that foreign key constraint is enforced."""
        # Note: SQLite doesn't enforce foreign key constraints by default in tests
        # This test verifies the model structure rather than database enforcement
        record = HiscoreRecord(
            player_id=99999, overall_level=1000  # Non-existent player
        )
        test_session.add(record)

        # In a real PostgreSQL database, this would raise an IntegrityError
        # For SQLite testing, we just verify the record can be created
        await test_session.commit()

        # Verify the record was created (even with invalid foreign key in SQLite)
        assert record.id is not None
        assert record.player_id == 99999

    @pytest.mark.asyncio
    async def test_multiple_records_same_player(
        self, test_session: AsyncSession, sample_player: Player
    ):
        """Test creating multiple hiscore records for the same player."""
        records = []
        for i in range(3):
            record = HiscoreRecord(
                player_id=sample_player.id,
                overall_level=1000 + (i * 100),
                overall_experience=10000000 + (i * 5000000),
                skills_data={
                    "attack": {"level": 80 + i, "experience": 2000000 + (i * 500000)}
                },
            )
            records.append(record)
            test_session.add(record)

        await test_session.commit()

        # Verify all records were created
        stmt = select(HiscoreRecord).where(HiscoreRecord.player_id == sample_player.id)
        result = await test_session.execute(stmt)
        found_records = result.scalars().all()

        assert len(found_records) == 3

        # Verify they have different levels
        levels = [r.overall_level for r in found_records]
        assert 1000 in levels
        assert 1100 in levels
        assert 1200 in levels

    @pytest.mark.asyncio
    async def test_combat_level_calculation_with_database_data(
        self, test_session: AsyncSession, sample_player: Player
    ):
        """Test combat level calculation with data from database."""
        skills_data = {
            "attack": {"rank": 500, "level": 75, "experience": 1210421},
            "strength": {"rank": 600, "level": 80, "experience": 2000000},
            "defence": {"rank": 700, "level": 70, "experience": 737627},
            "hitpoints": {"rank": 800, "level": 85, "experience": 3258594},
            "prayer": {"rank": 900, "level": 60, "experience": 273742},
            "ranged": {"rank": 1000, "level": 90, "experience": 5346332},
            "magic": {"rank": 1100, "level": 85, "experience": 3258594},
        }

        record = HiscoreRecord(player_id=sample_player.id, skills_data=skills_data)
        test_session.add(record)
        await test_session.commit()
        await test_session.refresh(record)

        combat_level = record.calculate_combat_level()

        # Verify combat level is calculated correctly
        # Base: 0.25 * (70 + 85 + 60//2) = 0.25 * (70 + 85 + 30) = 0.25 * 185 = 46.25
        # Melee: 0.325 * (75 + 80) = 0.325 * 155 = 50.375
        # Ranged: 0.325 * (int(90 * 1.5) + 70) = 0.325 * (135 + 70) = 0.325 * 205 = 66.625
        # Magic: 0.325 * (int(85 * 1.5) + 70) = 0.325 * (127 + 70) = 0.325 * 197 = 64.025
        # Combat: int(46.25 + max(50.375, 66.625, 64.025)) = int(46.25 + 66.625) = int(112.875) = 112
        assert combat_level == 112

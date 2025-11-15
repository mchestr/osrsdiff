"""Tests for summary service."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import InsufficientDataError, PlayerNotFoundError
from app.models.hiscore import HiscoreRecord
from app.models.player import Player
from app.models.player_summary import PlayerSummary
from app.services.summary import SummaryGenerationError, SummaryService


class TestSummaryService:
    """Test cases for SummaryService."""

    @pytest.fixture
    def summary_service(self, test_session):
        """Create a summary service instance for testing."""
        return SummaryService(test_session)

    @pytest.fixture
    async def test_player_with_history(self, test_session):
        """Create a test player with hiscore records."""
        player = Player(username="summaryPlayer")
        test_session.add(player)
        await test_session.flush()

        # Create records over the last 7 days
        base_date = datetime.now(timezone.utc) - timedelta(days=7)

        for i in range(8):
            record_date = base_date + timedelta(days=i)
            record = HiscoreRecord(
                player_id=player.id,
                fetched_at=record_date,
                overall_level=1500 + (i * 5),
                overall_experience=50000000 + (i * 150000),
                skills_data={
                    "attack": {
                        "rank": 500 - i,
                        "level": 99,
                        "experience": 13034431 + (i * 100000),
                    },
                    "defence": {
                        "rank": 600 - i,
                        "level": 90 + i,
                        "experience": 5346332 + (i * 50000),
                    },
                },
                bosses_data={
                    "zulrah": {
                        "rank": 1000 - (i * 5),
                        "kc": 500 + (i * 10),
                    },
                },
            )
            test_session.add(record)

        await test_session.commit()
        await test_session.refresh(player)
        return player

    @pytest.mark.asyncio
    async def test_generate_summary_for_player_success(
        self, summary_service, test_player_with_history
    ):
        """Test successful summary generation for a player."""
        with patch("openai.AsyncOpenAI") as mock_openai:
            # Mock OpenAI response
            mock_response = MagicMock()
            mock_response.choices = [
                MagicMock(
                    message=MagicMock(
                        content="This player has made excellent progress!"
                    )
                )
            ]
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(
                return_value=mock_response
            )
            mock_openai.return_value = mock_client

            # Mock settings
            with patch("app.services.summary.settings") as mock_settings:
                mock_settings.openai.api_key = "test-key"
                mock_settings.openai.model = "gpt-4o-mini"
                mock_settings.openai.max_tokens = 1000
                mock_settings.openai.temperature = 0.7

                summary = await summary_service.generate_summary_for_player(
                    test_player_with_history.id
                )

                assert summary is not None
                assert summary.player_id == test_player_with_history.id
                assert (
                    summary.summary_text
                    == "This player has made excellent progress!"
                )
                assert summary.model_used == "gpt-4o-mini"
                assert summary.period_start is not None
                assert summary.period_end is not None

    @pytest.mark.asyncio
    async def test_generate_summary_for_player_not_found(
        self, summary_service
    ):
        """Test summary generation for non-existent player."""
        with pytest.raises(PlayerNotFoundError):
            await summary_service.generate_summary_for_player(99999)

    @pytest.mark.asyncio
    async def test_generate_summary_for_player_insufficient_data(
        self, summary_service, test_session
    ):
        """Test summary generation with insufficient data."""
        # Create player with no records
        player = Player(username="noDataPlayer")
        test_session.add(player)
        await test_session.commit()

        with pytest.raises(InsufficientDataError):
            await summary_service.generate_summary_for_player(player.id)

    @pytest.mark.asyncio
    async def test_generate_summary_no_api_key(
        self, summary_service, test_player_with_history
    ):
        """Test summary generation fails when API key is missing."""
        with patch("app.services.summary.settings") as mock_settings:
            mock_settings.openai.api_key = None

            with pytest.raises(SummaryGenerationError) as exc_info:
                await summary_service.generate_summary_for_player(
                    test_player_with_history.id
                )

            assert "API key not configured" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_summary_openai_error(
        self, summary_service, test_player_with_history
    ):
        """Test summary generation handles OpenAI API errors."""
        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(
                side_effect=Exception("OpenAI API error")
            )
            mock_openai.return_value = mock_client

            with patch("app.services.summary.settings") as mock_settings:
                mock_settings.openai.api_key = "test-key"
                mock_settings.openai.model = "gpt-4o-mini"
                mock_settings.openai.max_tokens = 1000
                mock_settings.openai.temperature = 0.7

                with pytest.raises(SummaryGenerationError):
                    await summary_service.generate_summary_for_player(
                        test_player_with_history.id
                    )

    @pytest.mark.asyncio
    async def test_get_recent_summary(
        self, summary_service, test_player_with_history, test_session
    ):
        """Test retrieving recent summary."""
        # Create a recent summary
        summary = PlayerSummary(
            player_id=test_player_with_history.id,
            period_start=datetime.now(timezone.utc) - timedelta(days=7),
            period_end=datetime.now(timezone.utc),
            summary_text="Recent summary",
        )
        test_session.add(summary)
        await test_session.commit()

        recent = await summary_service._get_recent_summary(
            test_player_with_history.id, hours=24
        )

        assert recent is not None
        assert recent.summary_text == "Recent summary"

    @pytest.mark.asyncio
    async def test_get_recent_summary_none(
        self, summary_service, test_player_with_history, test_session
    ):
        """Test retrieving recent summary when none exists."""
        recent = await summary_service._get_recent_summary(
            test_player_with_history.id, hours=1
        )

        assert recent is None

    @pytest.mark.asyncio
    async def test_generate_summary_skips_recent(
        self, summary_service, test_player_with_history, test_session
    ):
        """Test that summary generation skips if recent summary exists."""
        # Create a recent summary
        summary = PlayerSummary(
            player_id=test_player_with_history.id,
            period_start=datetime.now(timezone.utc) - timedelta(days=7),
            period_end=datetime.now(timezone.utc),
            summary_text="Recent summary",
        )
        test_session.add(summary)
        await test_session.commit()

        # Try to generate (should return existing)
        recent = await summary_service.generate_summary_for_player(
            test_player_with_history.id, force_regenerate=False
        )

        assert recent.id == summary.id
        assert recent.summary_text == "Recent summary"

    @pytest.mark.asyncio
    async def test_generate_summary_force_regenerate(
        self, summary_service, test_player_with_history, test_session
    ):
        """Test force regeneration of summary."""
        # Create an old summary
        old_summary = PlayerSummary(
            player_id=test_player_with_history.id,
            period_start=datetime.now(timezone.utc) - timedelta(days=14),
            period_end=datetime.now(timezone.utc) - timedelta(days=7),
            summary_text="Old summary",
        )
        test_session.add(old_summary)
        await test_session.commit()

        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_response = MagicMock()
            mock_response.choices = [
                MagicMock(message=MagicMock(content="New summary!"))
            ]
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(
                return_value=mock_response
            )
            mock_openai.return_value = mock_client

            with patch("app.services.summary.settings") as mock_settings:
                mock_settings.openai.api_key = "test-key"
                mock_settings.openai.model = "gpt-4o-mini"
                mock_settings.openai.max_tokens = 1000
                mock_settings.openai.temperature = 0.7

                new_summary = (
                    await summary_service.generate_summary_for_player(
                        test_player_with_history.id, force_regenerate=True
                    )
                )

                assert new_summary.id != old_summary.id
                assert new_summary.summary_text == "New summary!"

    @pytest.mark.asyncio
    async def test_generate_summaries_for_all_players(
        self, summary_service, test_session
    ):
        """Test generating summaries for all active players."""
        # Create multiple players
        players = []
        for i in range(3):
            player = Player(username=f"player{i}")
            test_session.add(player)
            await test_session.flush()

            # Add some records
            record = HiscoreRecord(
                player_id=player.id,
                fetched_at=datetime.now(timezone.utc),
                overall_level=1500,
                overall_experience=50000000,
                skills_data={
                    "attack": {
                        "rank": 500,
                        "level": 99,
                        "experience": 13034431,
                    }
                },
            )
            test_session.add(record)
            players.append(player)

        await test_session.commit()

        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_response = MagicMock()
            mock_response.choices = [
                MagicMock(message=MagicMock(content="Summary text"))
            ]
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(
                return_value=mock_response
            )
            mock_openai.return_value = mock_client

            with patch("app.services.summary.settings") as mock_settings:
                mock_settings.openai.api_key = "test-key"
                mock_settings.openai.model = "gpt-4o-mini"
                mock_settings.openai.max_tokens = 1000
                mock_settings.openai.temperature = 0.7

                summaries = (
                    await summary_service.generate_summaries_for_all_players()
                )

                assert len(summaries) == 3
                assert all(s.summary_text == "Summary text" for s in summaries)

    @pytest.mark.asyncio
    async def test_create_summary_prompt(self, summary_service):
        """Test prompt creation."""
        day_data = {
            "progress": {
                "experience_gained": {
                    "overall": 100000,
                    "attack": 50000,
                    "defence": 30000,
                },
                "levels_gained": {"attack": 0, "defence": 1},
                "boss_kills_gained": {"zulrah": 10},
            }
        }
        week_data = {
            "progress": {
                "experience_gained": {
                    "overall": 500000,
                    "attack": 200000,
                    "defence": 150000,
                },
                "levels_gained": {"attack": 0, "defence": 2},
                "boss_kills_gained": {"zulrah": 50},
            }
        }

        prompt = summary_service._create_summary_prompt(
            "testplayer", day_data, week_data
        )

        assert "testplayer" in prompt
        assert "100,000" in prompt or "100000" in prompt
        assert "500,000" in prompt or "500000" in prompt
        assert "Attack" in prompt or "attack" in prompt
        assert "Defence" in prompt or "defence" in prompt

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
            # Mock OpenAI response with usage data
            mock_usage = MagicMock()
            mock_usage.prompt_tokens = 100
            mock_usage.completion_tokens = 50
            mock_usage.total_tokens = 150

            mock_response = MagicMock()
            mock_response.choices = [
                MagicMock(
                    message=MagicMock(
                        content='{"summary": "Test summary", "points": ["Point 1"]}'
                    ),
                    finish_reason="stop",
                )
            ]
            mock_response.usage = mock_usage
            mock_response.id = "test-response-id"

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
                    "summary" in summary.summary_text
                    or "points" in summary.summary_text
                )
                assert summary.model_used == "gpt-4o-mini"
                assert summary.period_start is not None
                assert summary.period_end is not None
                assert summary.prompt_tokens == 100
                assert summary.completion_tokens == 50
                assert summary.total_tokens == 150
                assert summary.finish_reason == "stop"
                assert summary.response_id == "test-response-id"

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
            prompt_tokens=None,
            completion_tokens=None,
            total_tokens=None,
            finish_reason=None,
            response_id=None,
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
            prompt_tokens=None,
            completion_tokens=None,
            total_tokens=None,
            finish_reason=None,
            response_id=None,
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
            prompt_tokens=None,
            completion_tokens=None,
            total_tokens=None,
            finish_reason=None,
            response_id=None,
        )
        test_session.add(old_summary)
        await test_session.commit()

        with patch("openai.AsyncOpenAI") as mock_openai:
            # Mock OpenAI response with usage data
            mock_usage = MagicMock()
            mock_usage.prompt_tokens = 100
            mock_usage.completion_tokens = 50
            mock_usage.total_tokens = 150

            mock_response = MagicMock()
            mock_response.choices = [
                MagicMock(
                    message=MagicMock(
                        content='{"summary": "New summary!", "points": ["Point 1"]}'
                    ),
                    finish_reason="stop",
                )
            ]
            mock_response.usage = mock_usage
            mock_response.id = "test-response-id"

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

                assert new_summary is not None
                assert new_summary.id != old_summary.id
                assert (
                    "New summary!" in new_summary.summary_text
                    or "points" in new_summary.summary_text
                )

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

            # Add records with progress (one old, one new to show progress)
            old_record = HiscoreRecord(
                player_id=player.id,
                fetched_at=datetime.now(timezone.utc) - timedelta(days=7),
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
            new_record = HiscoreRecord(
                player_id=player.id,
                fetched_at=datetime.now(timezone.utc),
                overall_level=1501,
                overall_experience=51000000,
                skills_data={
                    "attack": {
                        "rank": 499,
                        "level": 99,
                        "experience": 13134431,
                    }
                },
            )
            test_session.add(old_record)
            test_session.add(new_record)
            players.append(player)

        await test_session.commit()

        with patch("openai.AsyncOpenAI") as mock_openai:
            # Mock OpenAI response with usage data
            mock_usage = MagicMock()
            mock_usage.prompt_tokens = 100
            mock_usage.completion_tokens = 50
            mock_usage.total_tokens = 150

            mock_response = MagicMock()
            mock_response.choices = [
                MagicMock(
                    message=MagicMock(
                        content='{"summary": "Summary text", "points": ["Point 1"]}'
                    ),
                    finish_reason="stop",
                )
            ]
            mock_response.usage = mock_usage
            mock_response.id = "test-response-id"

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
                assert all(s is not None for s in summaries)
                assert all(
                    "Summary text" in s.summary_text
                    or "points" in s.summary_text
                    for s in summaries
                )

    def test_load_system_prompt(self, summary_service):
        """Test loading system prompt from template."""
        prompt = summary_service._load_system_prompt()

        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "OSRS" in prompt or "RuneScape" in prompt
        assert "analyst" in prompt.lower()

    def test_load_system_prompt_fallback(self, summary_service):
        """Test system prompt raises error when template fails."""
        with patch("app.services.summary.render_template") as mock_render:
            mock_render.side_effect = Exception("Template not found")

            with pytest.raises(SummaryGenerationError) as exc_info:
                summary_service._load_system_prompt()

            assert "Cannot load system prompt template" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_summary_prompt(self, summary_service):
        """Test prompt creation with template."""
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
        assert "Last 24 hours" in prompt or "24 hours" in prompt
        assert "Last 7 days" in prompt or "7 days" in prompt

    def test_create_summary_prompt_fallback(self, summary_service):
        """Test prompt creation raises error when template fails."""
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

        with patch("app.services.summary.render_template") as mock_render:
            mock_render.side_effect = Exception("Template not found")

            with pytest.raises(SummaryGenerationError) as exc_info:
                summary_service._create_summary_prompt(
                    "testplayer", day_data, week_data
                )

            assert "Cannot load user prompt template" in str(exc_info.value)

    def test_create_summary_prompt_no_top_skills(self, summary_service):
        """Test prompt creation when no top skills."""
        day_data = {
            "progress": {
                "experience_gained": {"overall": 0},
                "levels_gained": {},
                "boss_kills_gained": {},
            }
        }
        week_data = {
            "progress": {
                "experience_gained": {"overall": 0},
                "levels_gained": {},
                "boss_kills_gained": {},
            }
        }

        prompt = summary_service._create_summary_prompt(
            "testplayer", day_data, week_data
        )

        assert "testplayer" in prompt
        assert "None" in prompt or "0" in prompt

    def test_create_summary_prompt_formatting(self, summary_service):
        """Test that prompt formatting matches expected format."""
        day_data = {
            "progress": {
                "experience_gained": {
                    "overall": 1234567,
                    "attack": 500000,
                    "strength": 300000,
                    "defence": 200000,
                },
                "levels_gained": {"attack": 1, "defence": 1},
                "boss_kills_gained": {"zulrah": 25, "vorkath": 10},
            }
        }
        week_data = {
            "progress": {
                "experience_gained": {
                    "overall": 5000000,
                    "attack": 2000000,
                    "strength": 1500000,
                    "defence": 1000000,
                },
                "levels_gained": {"attack": 2, "defence": 2},
                "boss_kills_gained": {"zulrah": 100, "vorkath": 50},
            }
        }

        prompt = summary_service._create_summary_prompt(
            "TestPlayer123", day_data, week_data
        )

        # Check XP formatting with commas
        assert "1,234,567" in prompt or "1234567" in prompt
        assert "5,000,000" in prompt or "5000000" in prompt

        # Check skill formatting
        assert "Attack" in prompt or "attack" in prompt
        assert "Strength" in prompt or "strength" in prompt

        # Check totals
        assert "2" in prompt  # levels gained
        # Check boss kills (formatted as "Zulrah (25 KC), Vorkath (10 KC)")
        assert "Zulrah" in prompt or "zulrah" in prompt
        assert "Vorkath" in prompt or "vorkath" in prompt
        assert "25" in prompt or "100" in prompt  # boss kill counts

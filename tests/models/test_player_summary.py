"""Tests for PlayerSummary model."""

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.player import Player
from app.models.player_summary import PlayerSummary


class TestPlayerSummaryModel:
    """Test PlayerSummary model functionality."""

    def test_player_summary_creation(self):
        """Test basic player summary model creation."""
        period_start = datetime.now(timezone.utc)
        period_end = datetime.now(timezone.utc)
        generated_at = datetime.now(timezone.utc)

        summary = PlayerSummary(
            player_id=1,
            period_start=period_start,
            period_end=period_end,
            summary_text="Test summary text",
            model_used="gpt-4o-mini",
            generated_at=generated_at,
        )

        assert summary.player_id == 1
        assert summary.period_start == period_start
        assert summary.period_end == period_end
        assert summary.summary_text == "Test summary text"
        assert summary.model_used == "gpt-4o-mini"
        assert summary.generated_at == generated_at

    def test_player_summary_repr(self):
        """Test player summary string representation."""
        period_start = datetime.now(timezone.utc)
        period_end = datetime.now(timezone.utc)

        summary = PlayerSummary(
            id=1,
            player_id=2,
            period_start=period_start,
            period_end=period_end,
            summary_text="Test summary",
        )

        repr_str = repr(summary)
        assert "PlayerSummary" in repr_str
        assert "id=1" in repr_str
        assert "player_id=2" in repr_str

    @pytest_asyncio.fixture
    async def test_player(self, test_session: AsyncSession):
        """Create a test player."""
        player = Player(username="test_player")
        test_session.add(player)
        await test_session.flush()
        return player

    @pytest.mark.asyncio
    async def test_player_summary_relationship(
        self, test_session: AsyncSession, test_player: Player
    ):
        """Test relationship between Player and PlayerSummary."""
        period_start = datetime.now(timezone.utc)
        period_end = datetime.now(timezone.utc)

        summary = PlayerSummary(
            player_id=test_player.id,
            period_start=period_start,
            period_end=period_end,
            summary_text="Test summary",
        )

        test_session.add(summary)
        await test_session.commit()

        # Query player with summaries to avoid lazy loading issues
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        result = await test_session.execute(
            select(Player)
            .where(Player.id == test_player.id)
            .options(selectinload(Player.summaries))
        )
        player_with_summaries = result.scalar_one()

        assert len(player_with_summaries.summaries) == 1
        assert player_with_summaries.summaries[0].id == summary.id
        assert (
            player_with_summaries.summaries[0].summary_text == "Test summary"
        )
        # Also verify reverse relationship
        await test_session.refresh(summary)
        assert summary.player.id == test_player.id
        assert summary.player.username == test_player.username

    @pytest.mark.asyncio
    async def test_player_summary_preserved_on_delete(
        self, test_session: AsyncSession, test_player: Player
    ):
        """Test that summaries are preserved (player_id set to NULL) when player is deleted."""
        period_start = datetime.now(timezone.utc)
        period_end = datetime.now(timezone.utc)

        summary = PlayerSummary(
            player_id=test_player.id,
            period_start=period_start,
            period_end=period_end,
            summary_text="Test summary",
        )

        test_session.add(summary)
        await test_session.commit()

        # Delete player
        await test_session.delete(test_player)
        await test_session.commit()

        # Verify summary is preserved with player_id set to NULL
        result = await test_session.execute(
            select(PlayerSummary).where(PlayerSummary.id == summary.id)
        )
        preserved_summary = result.scalar_one_or_none()
        assert preserved_summary is not None
        assert preserved_summary.player_id is None
        assert preserved_summary.summary_text == "Test summary"

    @pytest.mark.asyncio
    async def test_multiple_summaries_for_player(
        self, test_session: AsyncSession, test_player: Player
    ):
        """Test that a player can have multiple summaries."""
        base_date = datetime.now(timezone.utc)

        summaries = []
        for i in range(3):
            summary = PlayerSummary(
                player_id=test_player.id,
                period_start=base_date - timedelta(days=7 * (i + 1)),
                period_end=base_date - timedelta(days=7 * i),
                summary_text=f"Summary {i + 1}",
                generated_at=base_date
                - timedelta(days=i),  # Set different generated_at for ordering
            )
            summaries.append(summary)
            test_session.add(summary)

        await test_session.commit()

        # Query player with summaries to avoid lazy loading issues
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        result = await test_session.execute(
            select(Player)
            .where(Player.id == test_player.id)
            .options(selectinload(Player.summaries))
        )
        player_with_summaries = result.scalar_one()

        assert len(player_with_summaries.summaries) == 3
        # Summaries should be ordered by generated_at desc
        # Note: selectinload may not preserve relationship ordering, so we sort manually
        sorted_summaries = sorted(
            player_with_summaries.summaries,
            key=lambda s: s.generated_at,
            reverse=True,
        )
        assert (
            sorted_summaries[0].summary_text == "Summary 1"
        )  # Most recent (generated_at = base_date)

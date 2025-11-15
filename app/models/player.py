from __future__ import annotations

import re
from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .player_type import PlayerType

if TYPE_CHECKING:
    from .hiscore import HiscoreRecord
    from .player_summary import PlayerSummary


class Player(Base):
    """
    Model representing an OSRS player being tracked.

    This model stores basic player information and metadata about tracking,
    with relationships to historical hiscore records.
    """

    __tablename__ = "players"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True)

    # Player identification
    username: Mapped[str] = mapped_column(
        String(12),
        unique=True,
        nullable=False,
        index=True,
        doc="OSRS username (1-12 characters, alphanumeric plus spaces, hyphens, underscores)",
    )

    # Tracking metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="When the player was added to tracking",
    )

    last_fetched: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When hiscore data was last successfully fetched",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether the player is actively being tracked",
    )

    fetch_interval_minutes: Mapped[int] = mapped_column(
        Integer,
        default=1440,
        nullable=False,
        doc="How often to fetch hiscore data (in minutes)",
    )

    # TaskIQ scheduler integration
    schedule_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        doc="TaskIQ schedule ID for this player's fetch task",
    )

    # Game mode classification
    game_mode: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        index=True,
        doc="Player game mode (regular, ironman, hardcore, ultimate)",
    )

    # Relationships
    hiscore_records: Mapped[List[HiscoreRecord]] = relationship(
        "HiscoreRecord",
        back_populates="player",
        cascade="all, delete-orphan",
        order_by="HiscoreRecord.fetched_at.desc()",
        doc="Historical hiscore records for this player",
    )

    summaries: Mapped[List["PlayerSummary"]] = relationship(
        "PlayerSummary",
        back_populates="player",
        cascade="save-update, merge",
        order_by="PlayerSummary.generated_at.desc()",
        doc="AI-generated progress summaries for this player (preserved when player is deleted)",
    )

    def __init__(self, **kwargs: Any) -> None:
        """Initialize Player with proper defaults."""
        # Set defaults if not provided
        if "is_active" not in kwargs:
            kwargs["is_active"] = True
        if "fetch_interval_minutes" not in kwargs:
            kwargs["fetch_interval_minutes"] = 1440
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        """String representation of the player."""
        return f"<Player(id={self.id}, username='{self.username}', active={self.is_active})>"

    @classmethod
    def validate_username(cls, username: str) -> bool:
        """
        Validate OSRS username format.

        OSRS usernames must be:
        - 1-12 characters long
        - Contain only letters, numbers, spaces, hyphens, and underscores
        - Not start or end with spaces

        Args:
            username: The username to validate

        Returns:
            bool: True if username is valid, False otherwise
        """
        if not username or len(username) < 1 or len(username) > 12:
            return False

        # Check for valid characters only
        if not re.match(r"^[a-zA-Z0-9 _-]+$", username):
            return False

        # Cannot start or end with spaces
        if username.startswith(" ") or username.endswith(" "):
            return False

        return True

    @property
    def latest_hiscore(self) -> Optional[HiscoreRecord]:
        """Get the most recent hiscore record for this player."""
        if self.hiscore_records:
            return self.hiscore_records[
                0
            ]  # Already ordered by fetched_at desc
        return None

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .player import Player


class HiscoreRecord(Base):
    """
    Model representing a snapshot of OSRS hiscore data for a player.

    This model stores both overall stats and detailed skill/boss data
    using JSON columns for flexibility as the OSRS API may add new
    skills or bosses over time.
    """

    __tablename__ = "hiscore_records"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True)

    # Foreign key to player
    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Reference to the player this record belongs to",
    )

    # Timestamp
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
        doc="When this hiscore data was fetched from OSRS API",
    )

    # Overall stats (commonly queried, so stored as separate columns)
    overall_rank: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Overall rank on hiscores (null if unranked)",
    )

    overall_level: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, doc="Total level across all skills"
    )

    overall_experience: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, doc="Total experience across all skills"
    )

    # Detailed data stored as JSON for flexibility
    skills_data: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        doc="Detailed skills data: {skill_name: {rank: int, level: int, experience: int}}",
    )

    bosses_data: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        doc="Boss kill counts data: {boss_name: {rank: int, kill_count: int}}",
    )

    # Relationships
    player: Mapped[Player] = relationship(
        "Player",
        back_populates="hiscore_records",
        doc="The player this hiscore record belongs to",
    )

    def __init__(self, **kwargs: Any) -> None:
        """Initialize HiscoreRecord with proper defaults."""
        # Set defaults if not provided
        if "skills_data" not in kwargs:
            kwargs["skills_data"] = {}
        if "bosses_data" not in kwargs:
            kwargs["bosses_data"] = {}
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        """String representation of the hiscore record."""
        return (
            f"<HiscoreRecord(id={self.id}, player_id={self.player_id}, "
            f"fetched_at={self.fetched_at}, overall_level={self.overall_level})>"
        )

    def get_skill_data(
        self, skill_name: str
    ) -> Optional[Dict[str, Optional[int]]]:
        """
        Get data for a specific skill.

        Args:
            skill_name: Name of the skill (e.g., 'attack', 'defence', 'overall')

        Returns:
            Dict with rank, level, and experience, or None if skill not found
        """
        skill_name_lower = skill_name.lower()
        # Handle "overall" as a special case since it's stored in separate columns
        if skill_name_lower == "overall":
            return {
                "rank": self.overall_rank,
                "level": self.overall_level,
                "experience": self.overall_experience,
            }
        return self.skills_data.get(skill_name_lower)

    def get_boss_data(self, boss_name: str) -> Optional[Dict[str, int]]:
        """
        Get data for a specific boss.

        Args:
            boss_name: Name of the boss (e.g., 'abyssal_sire', 'zulrah')

        Returns:
            Dict with rank and kill_count, or None if boss not found
        """
        return self.bosses_data.get(boss_name.lower())

    def get_skill_level(self, skill_name: str) -> Optional[int]:
        """Get the level for a specific skill."""
        # Handle "overall" as a special case for performance
        if skill_name.lower() == "overall":
            return self.overall_level
        skill_data = self.get_skill_data(skill_name)
        return skill_data.get("level") if skill_data else None

    def get_skill_experience(self, skill_name: str) -> Optional[int]:
        """Get the experience for a specific skill."""
        # Handle "overall" as a special case for performance
        if skill_name.lower() == "overall":
            return self.overall_experience
        skill_data = self.get_skill_data(skill_name)
        return skill_data.get("experience") if skill_data else None

    def get_boss_kills(self, boss_name: str) -> Optional[int]:
        """Get the kill count for a specific boss."""
        boss_data = self.get_boss_data(boss_name)
        return boss_data.get("kill_count") if boss_data else None

    @property
    def total_skills(self) -> int:
        """Get the number of skills with data."""
        return len(self.skills_data) if self.skills_data else 0

    @property
    def total_bosses(self) -> int:
        """Get the number of bosses with data."""
        return len(self.bosses_data) if self.bosses_data else 0

    def calculate_combat_level(self) -> Optional[int]:
        """
        Calculate combat level from skill levels using the official OSRS formula.

        Returns:
            Combat level or None if required skills are missing
        """
        required_skills = [
            "attack",
            "strength",
            "defence",
            "hitpoints",
            "prayer",
            "ranged",
            "magic",
        ]
        levels = {}

        for skill in required_skills:
            level = self.get_skill_level(skill)
            if level is None:
                return None
            levels[skill] = level

        # OSRS combat level formula
        # Base = 0.25 * (Defence + Hitpoints + floor(Prayer/2))
        base = 0.25 * (
            levels["defence"] + levels["hitpoints"] + levels["prayer"] // 2
        )

        # Melee = 0.325 * (Attack + Strength)
        melee = 0.325 * (levels["attack"] + levels["strength"])

        # Ranged = 0.325 * floor(Ranged * 1.5)
        ranged = 0.325 * int(levels["ranged"] * 1.5)

        # Magic = 0.325 * (floor(Magic * 1.5) + Defence)
        magic = 0.325 * int(levels["magic"] * 1.5)

        return int(base + max(melee, ranged, magic))

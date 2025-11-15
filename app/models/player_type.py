"""Player type enum for OSRS game modes."""

from enum import Enum


class PlayerType(str, Enum):
    """OSRS player game mode types."""

    REGULAR = "regular"
    IRONMAN = "ironman"
    HARDCORE = "hardcore"
    ULTIMATE = "ultimate"

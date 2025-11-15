"""Common utility functions used across the application."""

from datetime import datetime, timezone
from typing import Optional

from app.exceptions import InvalidUsernameError
from app.models.player import Player


def normalize_username(username: Optional[str]) -> str:
    """
    Normalize and validate a username.

    Args:
        username: Raw username string

    Returns:
        Normalized username (stripped)

    Raises:
        InvalidUsernameError: If username is empty or invalid format
    """
    if not username:
        raise InvalidUsernameError("Username cannot be empty")

    normalized = username.strip()

    # Check for empty after stripping (handles whitespace-only strings)
    if not normalized:
        raise InvalidUsernameError("Username cannot be empty")

    if not Player.validate_username(normalized):
        raise InvalidUsernameError(
            f"Invalid username format: '{normalized}'. "
            "Username must be 1-12 characters, contain only letters, numbers, "
            "spaces, hyphens, and underscores, and not start/end with spaces."
        )

    return normalized


def ensure_timezone_aware(dt: datetime) -> datetime:
    """
    Ensure a datetime is timezone-aware (assumes UTC if naive).

    Args:
        dt: Datetime that may or may not be timezone-aware

    Returns:
        Timezone-aware datetime (UTC if originally naive)
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def parse_iso_datetime(date_str: str) -> datetime:
    """
    Parse an ISO format datetime string, handling 'Z' suffix.

    Args:
        date_str: ISO format datetime string (e.g., '2024-01-01T00:00:00Z')

    Returns:
        Parsed datetime object

    Raises:
        ValueError: If date string is invalid
    """
    # Replace 'Z' with '+00:00' for proper parsing
    normalized = date_str.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)

"""Tests for common utility functions."""

from datetime import datetime, timedelta, timezone

import pytest

from app.exceptions import InvalidUsernameError
from app.utils.common import (
    ensure_timezone_aware,
    normalize_username,
    parse_iso_datetime,
)


class TestNormalizeUsername:
    """Test username normalization utility."""

    def test_normalize_valid_username(self):
        """Test normalizing a valid username."""
        assert normalize_username("testplayer") == "testplayer"
        assert normalize_username("  testplayer  ") == "testplayer"
        assert normalize_username("test player") == "test player"
        assert normalize_username("test-player") == "test-player"
        assert normalize_username("test_player") == "test_player"

    def test_normalize_empty_username(self):
        """Test normalizing empty username raises error."""
        with pytest.raises(
            InvalidUsernameError, match="Username cannot be empty"
        ):
            normalize_username("")
        with pytest.raises(
            InvalidUsernameError, match="Username cannot be empty"
        ):
            normalize_username("   ")
        with pytest.raises(InvalidUsernameError):
            normalize_username(None)

    def test_normalize_invalid_format(self):
        """Test normalizing invalid username format raises error."""
        with pytest.raises(InvalidUsernameError):
            normalize_username("toolongname123")  # Too long (13 chars)
        with pytest.raises(InvalidUsernameError):
            normalize_username("user@name")  # Invalid character
        # Note: " user" and "user " are valid after normalization (stripped to "user")
        # The validation happens AFTER stripping, so leading/trailing spaces are removed


class TestEnsureTimezoneAware:
    """Test timezone awareness utility."""

    def test_naive_datetime_becomes_aware(self):
        """Test naive datetime becomes timezone-aware."""
        naive_dt = datetime(2024, 1, 1, 12, 0, 0)
        aware_dt = ensure_timezone_aware(naive_dt)

        assert aware_dt.tzinfo is not None
        assert aware_dt.tzinfo == timezone.utc
        assert aware_dt.year == 2024
        assert aware_dt.month == 1
        assert aware_dt.day == 1

    def test_aware_datetime_unchanged(self):
        """Test timezone-aware datetime is unchanged."""
        aware_dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = ensure_timezone_aware(aware_dt)

        assert result is aware_dt
        assert result.tzinfo == timezone.utc

    def test_different_timezone_preserved(self):
        """Test datetime with different timezone is preserved."""
        from datetime import timezone as tz

        # Create datetime with different timezone (e.g., EST)
        est = tz(timedelta(hours=-5))
        dt_with_tz = datetime(2024, 1, 1, 12, 0, 0, tzinfo=est)
        result = ensure_timezone_aware(dt_with_tz)

        assert result.tzinfo == est
        assert result is dt_with_tz


class TestParseIsoDatetime:
    """Test ISO datetime parsing utility."""

    def test_parse_with_z_suffix(self):
        """Test parsing datetime with Z suffix."""
        dt_str = "2024-01-01T12:00:00Z"
        result = parse_iso_datetime(dt_str)

        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 1
        assert result.hour == 12
        assert result.tzinfo == timezone.utc

    def test_parse_with_timezone_offset(self):
        """Test parsing datetime with timezone offset."""
        dt_str = "2024-01-01T12:00:00+00:00"
        result = parse_iso_datetime(dt_str)

        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.tzinfo is not None

    def test_parse_invalid_format(self):
        """Test parsing invalid datetime format raises error."""
        with pytest.raises(ValueError):
            parse_iso_datetime("invalid-date")
        with pytest.raises((ValueError, TypeError)):
            parse_iso_datetime("not-a-date")
        # Note: "2024-01-01" is actually valid ISO format (date only)
        # so it parses successfully, which is fine

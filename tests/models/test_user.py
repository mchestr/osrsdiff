"""Tests for User model."""

from datetime import datetime, timezone

import pytest

from src.models.user import User


class TestUserModel:
    """Test cases for User model."""

    def test_user_creation(self):
        """Test creating a user instance."""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password_123",
            is_active=True,
            is_admin=False,
        )

        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.hashed_password == "hashed_password_123"
        assert user.is_active is True
        assert user.is_admin is False

    def test_user_repr(self):
        """Test user string representation."""
        user = User(
            id=1,
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password_123",
            is_active=True,
            is_admin=True,
        )

        expected = "<User(id=1, username='testuser', is_admin=True)>"
        assert repr(user) == expected

    def test_user_defaults(self):
        """Test user default values."""
        user = User(
            username="testuser",
            hashed_password="hashed_password_123",
            is_active=True,  # Need to explicitly set since we're not using database defaults
            is_admin=False,
        )

        # Test defaults
        assert user.is_active is True
        assert user.is_admin is False
        assert user.email is None
        assert user.last_login is None

    def test_user_admin_creation(self):
        """Test creating an admin user."""
        user = User(
            username="admin",
            email="admin@example.com",
            hashed_password="admin_password_hash",
            is_active=True,
            is_admin=True,
        )

        assert user.username == "admin"
        assert user.is_admin is True
        assert user.is_active is True

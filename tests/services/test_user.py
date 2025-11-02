"""Tests for User service."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from src.models.user import User
from src.services.user import user_service


class TestUserService:
    """Test cases for UserService."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "test_password_123"
        hashed = user_service.hash_password(password)

        # Should return a string
        assert isinstance(hashed, str)
        # Should be different from original password
        assert hashed != password
        # Should start with bcrypt prefix
        assert hashed.startswith("$2b$")

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "test_password_123"
        hashed = user_service.hash_password(password)

        # Verification should succeed
        assert user_service.verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = user_service.hash_password(password)

        # Verification should fail
        assert user_service.verify_password(wrong_password, hashed) is False

    @pytest.mark.asyncio
    async def test_get_user_by_username_found(self):
        """Test getting user by username when user exists."""
        # Create a real user object for testing
        mock_user = User(
            id=1,
            username="testuser",
            hashed_password="hash",
            is_active=True,
            is_admin=False,
        )

        # Mock the entire method
        with patch.object(
            user_service, "get_user_by_username", return_value=mock_user
        ) as mock_method:
            result = await user_service.get_user_by_username(
                AsyncMock(), "testuser"
            )

            assert result == mock_user
            mock_method.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_by_username_not_found(self):
        """Test getting user by username when user doesn't exist."""
        # Mock the entire method to return None
        with patch.object(
            user_service, "get_user_by_username", return_value=None
        ) as mock_method:
            result = await user_service.get_user_by_username(
                AsyncMock(), "nonexistent"
            )

            assert result is None
            mock_method.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_by_id_found(self):
        """Test getting user by ID when user exists."""
        # Create a real user object for testing
        mock_user = User(
            id=1,
            username="testuser",
            hashed_password="hash",
            is_active=True,
            is_admin=False,
        )

        # Mock the entire method
        with patch.object(
            user_service, "get_user_by_id", return_value=mock_user
        ) as mock_method:
            result = await user_service.get_user_by_id(AsyncMock(), 1)

            assert result == mock_user
            mock_method.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user(self):
        """Test creating a new user."""
        # Mock database session
        mock_db = AsyncMock()

        result = await user_service.create_user(
            mock_db,
            username="newuser",
            password="password123",
            email="new@example.com",
            is_admin=False,
        )

        # Verify user was created with correct properties
        assert result.username == "newuser"
        assert result.email == "new@example.com"
        assert result.is_admin is False
        assert result.is_active is True
        # Password should be hashed
        assert result.hashed_password != "password123"
        assert result.hashed_password.startswith("$2b$")

        # Verify database operations
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_admin_user(self):
        """Test creating an admin user."""
        # Mock database session
        mock_db = AsyncMock()

        result = await user_service.create_user(
            mock_db, username="admin", password="admin_password", is_admin=True
        )

        # Verify admin user was created
        assert result.username == "admin"
        assert result.is_admin is True
        assert result.is_active is True
        assert result.email is None

    @pytest.mark.asyncio
    async def test_authenticate_user_success(self):
        """Test successful user authentication."""
        # Create a user with known password
        password = "test_password"
        hashed_password = user_service.hash_password(password)
        mock_user = User(
            id=1,
            username="testuser",
            hashed_password=hashed_password,
            is_active=True,
        )

        # Mock database session
        mock_db = AsyncMock()

        # Mock get_user_by_username to return our user
        with patch.object(
            user_service, "get_user_by_username", return_value=mock_user
        ):
            result = await user_service.authenticate_user(
                mock_db, "testuser", password
            )

        assert result == mock_user
        # Verify last_login was updated
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self):
        """Test authentication when user doesn't exist."""
        # Mock database session
        mock_db = AsyncMock()

        # Mock get_user_by_username to return None
        with patch.object(
            user_service, "get_user_by_username", return_value=None
        ):
            result = await user_service.authenticate_user(
                mock_db, "nonexistent", "password"
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self):
        """Test authentication with wrong password."""
        # Create a user with known password
        password = "correct_password"
        hashed_password = user_service.hash_password(password)
        mock_user = User(
            id=1,
            username="testuser",
            hashed_password=hashed_password,
            is_active=True,
        )

        # Mock database session
        mock_db = AsyncMock()

        # Mock get_user_by_username to return our user
        with patch.object(
            user_service, "get_user_by_username", return_value=mock_user
        ):
            result = await user_service.authenticate_user(
                mock_db, "testuser", "wrong_password"
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_user_inactive(self):
        """Test authentication with inactive user."""
        # Create an inactive user
        password = "test_password"
        hashed_password = user_service.hash_password(password)
        mock_user = User(
            id=1,
            username="testuser",
            hashed_password=hashed_password,
            is_active=False,  # Inactive user
        )

        # Mock database session
        mock_db = AsyncMock()

        # Mock get_user_by_username to return our user
        with patch.object(
            user_service, "get_user_by_username", return_value=mock_user
        ):
            result = await user_service.authenticate_user(
                mock_db, "testuser", password
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_update_user_last_login(self):
        """Test updating user's last login timestamp."""
        # Mock user and database session
        mock_user = User(id=1, username="testuser", hashed_password="hash")
        mock_db = AsyncMock()

        # Mock get_user_by_id to return our user
        with patch.object(
            user_service, "get_user_by_id", return_value=mock_user
        ):
            await user_service.update_user_last_login(mock_db, 1)

        # Verify last_login was set and database was committed
        assert mock_user.last_login is not None
        assert isinstance(mock_user.last_login, datetime)
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_user_last_login_user_not_found(self):
        """Test updating last login for non-existent user."""
        # Mock database session
        mock_db = AsyncMock()

        # Mock get_user_by_id to return None
        with patch.object(user_service, "get_user_by_id", return_value=None):
            await user_service.update_user_last_login(mock_db, 999)

        # Should not commit if user not found
        mock_db.commit.assert_not_called()

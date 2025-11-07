"""Tests for authentication API dependencies."""

import pytest
from fastapi.security import HTTPAuthorizationCredentials

from app.api.auth_utils import get_current_user, get_optional_current_user
from app.exceptions import UnauthorizedError
from app.services.auth import auth_service


class TestAuthDependencies:
    """Test cases for authentication dependencies."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_user_data = {
            "sub": "test_user",
            "username": "testuser",
            "user_id": 123,
        }

    @pytest.mark.asyncio
    async def test_get_current_user_valid_token(self):
        """Test get_current_user with valid token."""
        # Create a valid access token
        token = auth_service.create_access_token(self.test_user_data)

        # Test the dependency - pass token string directly
        user = await get_current_user(token)

        assert user["sub"] == "test_user"
        assert user["username"] == "testuser"
        assert user["user_id"] == 123
        assert user["type"] == "access"

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self):
        """Test get_current_user with invalid token."""
        with pytest.raises(UnauthorizedError) as exc_info:
            await get_current_user("invalid_token")

        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_optional_current_user_valid_token(self):
        """Test get_optional_current_user with valid token."""
        # Create a valid access token
        token = auth_service.create_access_token(self.test_user_data)

        # Test the dependency
        user = await get_optional_current_user(token)

        assert user is not None
        assert user["sub"] == "test_user"
        assert user["username"] == "testuser"
        assert user["user_id"] == 123

    @pytest.mark.asyncio
    async def test_get_optional_current_user_no_token(self):
        """Test get_optional_current_user with no token."""
        user = await get_optional_current_user(None)
        assert user is None

    @pytest.mark.asyncio
    async def test_get_optional_current_user_invalid_token(self):
        """Test get_optional_current_user with invalid token."""
        user = await get_optional_current_user("invalid_token")
        assert user is None

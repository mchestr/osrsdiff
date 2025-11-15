"""Tests for authentication API dependencies."""

import pytest
from fastapi.security import HTTPAuthorizationCredentials

from app.api.auth_utils import (
    TokenRefreshRequest,
    TokenRefreshResponse,
    TokenResponse,
    get_current_user,
    get_current_user_bearer,
    get_optional_current_user,
    optional_auth,
    require_admin,
    require_auth,
)
from app.exceptions import ForbiddenError, UnauthorizedError
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
        self.test_admin_data = {
            "sub": "admin_user",
            "username": "admin",
            "user_id": 1,
            "is_admin": True,
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
    async def test_get_current_user_bearer_valid_token(self):
        """Test get_current_user_bearer with valid token."""
        token = auth_service.create_access_token(self.test_user_data)
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials=token
        )

        user = await get_current_user_bearer(credentials)

        assert user["sub"] == "test_user"
        assert user["username"] == "testuser"
        assert user["user_id"] == 123
        assert user["type"] == "access"

    @pytest.mark.asyncio
    async def test_get_current_user_bearer_invalid_token(self):
        """Test get_current_user_bearer with invalid token."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="invalid_token"
        )

        with pytest.raises(UnauthorizedError) as exc_info:
            await get_current_user_bearer(credentials)

        assert exc_info.value.status_code == 401

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

    @pytest.mark.asyncio
    async def test_require_auth_valid_user(self):
        """Test require_auth with valid user."""
        token = auth_service.create_access_token(self.test_user_data)
        user = await get_current_user(token)

        result = require_auth(user)
        assert result == user

    @pytest.mark.asyncio
    async def test_optional_auth_with_user(self):
        """Test optional_auth with valid user."""
        token = auth_service.create_access_token(self.test_user_data)
        user = await get_optional_current_user(token)

        result = optional_auth(user)
        assert result == user

    @pytest.mark.asyncio
    async def test_optional_auth_without_user(self):
        """Test optional_auth without user."""
        result = optional_auth(None)
        assert result is None

    @pytest.mark.asyncio
    async def test_require_admin_with_admin_user(self):
        """Test require_admin with admin user."""
        token = auth_service.create_access_token(self.test_admin_data)
        admin_user = await get_current_user(token)

        result = require_admin(admin_user)
        assert result == admin_user

    @pytest.mark.asyncio
    async def test_require_admin_with_non_admin_user(self):
        """Test require_admin with non-admin user."""
        token = auth_service.create_access_token(self.test_user_data)
        user = await get_current_user(token)

        with pytest.raises(ForbiddenError) as exc_info:
            require_admin(user)

        assert exc_info.value.status_code == 403
        assert "Admin privileges required" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_require_admin_with_user_missing_is_admin(self):
        """Test require_admin with user missing is_admin field."""
        user_data = {"sub": "test_user", "username": "testuser", "user_id": 123}
        token = auth_service.create_access_token(user_data)
        user = await get_current_user(token)

        with pytest.raises(ForbiddenError) as exc_info:
            require_admin(user)

        assert exc_info.value.status_code == 403


class TestAuthModels:
    """Test cases for authentication Pydantic models."""

    def test_token_response(self):
        """Test TokenResponse model."""
        response = TokenResponse(
            access_token="test_token", refresh_token="refresh_token"
        )

        assert response.access_token == "test_token"
        assert response.refresh_token == "refresh_token"
        assert response.token_type == "bearer"

    def test_token_response_default_token_type(self):
        """Test TokenResponse with default token_type."""
        response = TokenResponse(
            access_token="test_token", refresh_token="refresh_token"
        )

        assert response.token_type == "bearer"

    def test_token_refresh_request(self):
        """Test TokenRefreshRequest model."""
        request = TokenRefreshRequest(refresh_token="refresh_token")

        assert request.refresh_token == "refresh_token"

    def test_token_refresh_response(self):
        """Test TokenRefreshResponse model."""
        response = TokenRefreshResponse(access_token="new_access_token")

        assert response.access_token == "new_access_token"
        assert response.token_type == "bearer"

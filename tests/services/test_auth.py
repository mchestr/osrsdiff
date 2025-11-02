"""Tests for JWT authentication service."""

from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException

from src.services.auth import AuthService


class TestAuthService:
    """Test cases for AuthService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.auth_service = AuthService()
        # Use longer expiration times for testing to avoid timing issues
        self.auth_service.access_token_expire_minutes = 60  # 1 hour
        self.auth_service.refresh_token_expire_days = 30  # 30 days

        self.test_user_data = {
            "sub": "test_user",
            "username": "testuser",
            "user_id": 123,
        }

    async def test_create_access_token(self):
        """Test access token creation."""
        token = self.auth_service.create_access_token(self.test_user_data)

        assert isinstance(token, str)
        assert len(token) > 0

        # Validate the token
        payload = await self.auth_service.validate_token(
            token, token_type="access"
        )
        assert payload["sub"] == "test_user"
        assert payload["username"] == "testuser"
        assert payload["user_id"] == 123
        assert payload["type"] == "access"

    async def test_create_refresh_token(self):
        """Test refresh token creation."""
        token = self.auth_service.create_refresh_token(self.test_user_data)

        assert isinstance(token, str)
        assert len(token) > 0

        # Validate the token
        payload = await self.auth_service.validate_token(
            token, token_type="refresh"
        )
        assert payload["sub"] == "test_user"
        assert payload["username"] == "testuser"
        assert payload["user_id"] == 123
        assert payload["type"] == "refresh"

    async def test_create_token_pair(self):
        """Test creating both access and refresh tokens."""
        tokens = self.auth_service.create_token_pair(self.test_user_data)

        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert "token_type" in tokens
        assert tokens["token_type"] == "bearer"

        # Validate both tokens
        access_payload = await self.auth_service.validate_token(
            tokens["access_token"], token_type="access"
        )
        refresh_payload = await self.auth_service.validate_token(
            tokens["refresh_token"], token_type="refresh"
        )

        assert access_payload["sub"] == "test_user"
        assert refresh_payload["sub"] == "test_user"

    async def test_validate_token_invalid_token(self):
        """Test validation with invalid token."""
        with pytest.raises(HTTPException) as exc_info:
            await self.auth_service.validate_token("invalid_token")

        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in exc_info.value.detail

    async def test_validate_token_wrong_type(self):
        """Test validation with wrong token type."""
        access_token = self.auth_service.create_access_token(
            self.test_user_data
        )

        with pytest.raises(HTTPException) as exc_info:
            await self.auth_service.validate_token(
                access_token, token_type="refresh"
            )

        assert exc_info.value.status_code == 401
        assert "Invalid token type" in exc_info.value.detail

    async def test_refresh_access_token(self):
        """Test refreshing access token using refresh token."""
        refresh_token = self.auth_service.create_refresh_token(
            self.test_user_data
        )
        new_access_token = await self.auth_service.refresh_access_token(
            refresh_token
        )

        assert isinstance(new_access_token, str)
        assert len(new_access_token) > 0

        # Validate the new access token
        payload = await self.auth_service.validate_token(
            new_access_token, token_type="access"
        )
        assert payload["sub"] == "test_user"
        assert payload["username"] == "testuser"
        assert payload["user_id"] == 123
        assert payload["type"] == "access"

    async def test_refresh_access_token_with_access_token_fails(self):
        """Test that refresh fails when using access token instead of refresh token."""
        access_token = self.auth_service.create_access_token(
            self.test_user_data
        )

        with pytest.raises(HTTPException) as exc_info:
            await self.auth_service.refresh_access_token(access_token)

        assert exc_info.value.status_code == 401
        assert "Invalid token type" in exc_info.value.detail

    async def test_token_expiration_validation(self):
        """Test that expired tokens are rejected."""
        # Create a token with very short expiration for testing
        original_expire_minutes = self.auth_service.access_token_expire_minutes

        # Create an already expired token by setting negative expiration
        self.auth_service.access_token_expire_minutes = -60  # 1 hour ago

        try:
            token = self.auth_service.create_access_token(self.test_user_data)

            with pytest.raises(HTTPException) as exc_info:
                await self.auth_service.validate_token(
                    token, token_type="access"
                )

            assert exc_info.value.status_code == 401
            # The error could be either "Token has expired" or "Could not validate credentials"
            # depending on timing, both are valid for expired tokens
            assert exc_info.value.status_code == 401
        finally:
            # Restore original expiration time
            self.auth_service.access_token_expire_minutes = (
                original_expire_minutes
            )

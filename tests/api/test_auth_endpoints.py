"""Tests for authentication endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.auth_endpoints import router
from app.models.base import get_db_session
from app.models.user import User
from app.services.auth import auth_service


@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
    user = User(
        id=1,
        username="admin",
        email="admin@example.com",
        hashed_password="$2b$12$test_hash",
        is_active=True,
        is_admin=True,
    )
    return user


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    return AsyncMock()


@pytest.fixture
def app(mock_db_session):
    """Create FastAPI app for testing."""
    app = FastAPI()
    app.include_router(router)

    # Override database dependency
    app.dependency_overrides[get_db_session] = lambda: mock_db_session

    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


class TestAuthEndpoints:
    """Test cases for authentication endpoints."""

    @patch("app.services.auth.auth_service.authenticate_user")
    def test_login_success(self, mock_authenticate, client, mock_user):
        """Test successful login."""
        # Mock successful authentication
        mock_authenticate.return_value = mock_user

        # Use form data for OAuth2 endpoint
        response = client.post(
            "/auth/login", data={"username": "admin", "password": "admin"}
        )

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

        # Verify tokens are valid
        assert len(data["access_token"]) > 0
        assert len(data["refresh_token"]) > 0

    @patch("app.services.auth.auth_service.authenticate_user")
    def test_login_invalid_credentials(self, mock_authenticate, client):
        """Test login with invalid credentials."""
        # Mock failed authentication
        mock_authenticate.return_value = None

        # Use form data for OAuth2 endpoint
        response = client.post(
            "/auth/login", data={"username": "admin", "password": "wrong"}
        )

        assert response.status_code == 401
        assert "Invalid username or password" in response.json()["detail"]

    @patch("app.services.auth.auth_service.authenticate_user")
    def test_refresh_token_success(self, mock_authenticate, client, mock_user):
        """Test successful token refresh."""
        # Mock successful authentication
        mock_authenticate.return_value = mock_user

        # First login to get tokens using form data
        login_response = client.post(
            "/auth/login", data={"username": "admin", "password": "admin"}
        )
        tokens = login_response.json()

        # Use refresh token to get new access token
        response = client.post(
            "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        )

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert data["token_type"] == "bearer"

        # Verify new access token exists
        assert len(data["access_token"]) > 0

    def test_refresh_token_invalid(self, client):
        """Test refresh with invalid token."""
        response = client.post(
            "/auth/refresh", json={"refresh_token": "invalid_token"}
        )

        assert response.status_code == 401
        assert "Invalid refresh token" in response.json()["detail"]

    @patch("app.services.auth.auth_service.authenticate_user")
    def test_get_current_user_success(
        self, mock_authenticate, client, mock_user
    ):
        """Test getting current user info with valid token."""
        # Mock successful authentication
        mock_authenticate.return_value = mock_user

        # First login to get token using form data
        login_response = client.post(
            "/auth/login", data={"username": "admin", "password": "admin"}
        )
        token = login_response.json()["access_token"]

        # Use token to access protected endpoint
        response = client.get(
            "/auth/me", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["username"] == "admin"
        assert data["user_id"] == 1

    def test_get_current_user_no_token(self, client):
        """Test accessing protected endpoint without token."""
        response = client.get("/auth/me")

        assert (
            response.status_code == 401
        )  # FastAPI returns 401 for missing auth

    def test_get_current_user_invalid_token(self, client):
        """Test accessing protected endpoint with invalid token."""
        response = client.get(
            "/auth/me", headers={"Authorization": "Bearer invalid_token"}
        )

        assert response.status_code == 401

    @patch("app.services.auth.auth_service.authenticate_user")
    def test_logout_success(self, mock_authenticate, client, mock_user):
        """Test successful logout."""
        # Mock successful authentication
        mock_authenticate.return_value = mock_user

        # First login to get token using form data
        login_response = client.post(
            "/auth/login", data={"username": "admin", "password": "admin"}
        )
        token = login_response.json()["access_token"]

        # Logout
        response = client.post(
            "/auth/logout", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert "Successfully logged out" in response.json()["message"]

    def test_logout_without_token(self, client):
        """Test logout without authentication token."""
        response = client.post("/auth/logout")

        assert (
            response.status_code == 403
        )  # FastAPI returns 403 for missing auth

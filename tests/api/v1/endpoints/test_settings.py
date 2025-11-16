"""Tests for settings API endpoints - Security critical tests."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.api.auth_utils import require_admin
from app.api.v1.endpoints.settings import router
from app.exceptions import BaseAPIException, ForbiddenError, NotFoundError
from app.models.base import get_db_session
from app.models.setting import Setting


@pytest.fixture
def mock_admin_user():
    """Mock admin user."""
    return {"username": "admin", "user_id": 1, "is_admin": True}


@pytest.fixture
def mock_non_admin_user():
    """Mock non-admin user."""
    return {"username": "user", "user_id": 2, "is_admin": False}


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    return AsyncMock()


@pytest.fixture
def mock_setting():
    """Create a mock setting for testing."""
    return Setting(
        id=1,
        key="openai.api_key",
        value="sk-test123",
        display_name="OpenAI API Key",
        description="API key for OpenAI service",
        setting_type="string",
        allowed_values=None,
        is_secret=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_settings_list(mock_setting):
    """Create a list of mock settings."""
    return [
        mock_setting,
        Setting(
            id=2,
            key="openai.model",
            value="gpt-4o-mini",
            display_name="OpenAI Model",
            description="Model to use for OpenAI",
            setting_type="string",
            allowed_values=None,
            is_secret=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
    ]


@pytest.fixture
def app(mock_db_session):
    """Create FastAPI app for testing with mocked dependencies."""
    app = FastAPI()
    app.include_router(router)

    # Override database dependency
    app.dependency_overrides[get_db_session] = lambda: mock_db_session

    # Add exception handler for BaseAPIException
    @app.exception_handler(BaseAPIException)
    async def api_exception_handler(request, exc: BaseAPIException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "message": exc.message},
        )

    # Add exception handler for ForbiddenError
    @app.exception_handler(ForbiddenError)
    async def forbidden_handler(request, exc: ForbiddenError):
        return JSONResponse(
            status_code=403,
            content={"detail": exc.detail, "message": exc.message},
        )

    return app


@pytest.fixture
def admin_client(app, mock_db_session, mock_admin_user):
    """Create test client with admin user dependency overrides."""
    app.dependency_overrides[get_db_session] = lambda: mock_db_session
    app.dependency_overrides[require_admin] = lambda: mock_admin_user
    return TestClient(app)


@pytest.fixture
def non_admin_client(app, mock_db_session):
    """Create test client that will raise ForbiddenError for non-admin."""
    app.dependency_overrides[get_db_session] = lambda: mock_db_session

    def raise_forbidden():
        raise ForbiddenError("Admin privileges required")

    app.dependency_overrides[require_admin] = raise_forbidden
    return TestClient(app)


@pytest.fixture
def unauthenticated_client(app, mock_db_session):
    """Create test client without authentication."""
    app.dependency_overrides[get_db_session] = lambda: mock_db_session
    # Don't override require_admin, so it will fail authentication
    return TestClient(app)


class TestGetAllSettings:
    """Test GET /settings endpoint."""

    @pytest.mark.asyncio
    async def test_get_all_settings_admin_success(
        self, admin_client, mock_db_session, mock_settings_list
    ):
        """Test admin can successfully get all settings."""
        from app.services.setting import setting_service

        mock_db_session.execute = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = mock_settings_list
        mock_db_session.execute.return_value = mock_result

        with patch.object(
            setting_service,
            "get_all_settings",
            return_value=mock_settings_list,
        ):
            response = admin_client.get("/settings")

        assert response.status_code == 200
        data = response.json()
        assert "settings" in data
        assert len(data["settings"]) == 2
        assert data["settings"][0]["key"] == "openai.api_key"
        assert data["settings"][0]["is_secret"] is True
        assert data["settings"][1]["key"] == "openai.model"

    def test_get_all_settings_non_admin_forbidden(self, non_admin_client):
        """Test non-admin user cannot get all settings."""
        response = non_admin_client.get("/settings")
        assert response.status_code == 403
        assert "Admin privileges required" in response.json()["detail"]

    def test_get_all_settings_unauthenticated_forbidden(
        self, unauthenticated_client
    ):
        """Test unauthenticated user cannot get all settings."""
        response = unauthenticated_client.get("/settings")
        # Should fail at authentication level (401) or authorization (403)
        assert response.status_code in [401, 403]


class TestGetSetting:
    """Test GET /settings/{key} endpoint."""

    @pytest.mark.asyncio
    async def test_get_setting_admin_success(
        self, admin_client, mock_db_session, mock_setting
    ):
        """Test admin can successfully get a specific setting."""
        from app.services.setting import setting_service

        with patch.object(
            setting_service, "get_setting", return_value=mock_setting
        ):
            response = admin_client.get("/settings/openai.api_key")

        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "openai.api_key"
        assert data["value"] == "sk-test123"
        assert data["is_secret"] is True
        assert data["display_name"] == "OpenAI API Key"

    @pytest.mark.asyncio
    async def test_get_setting_not_found(self, admin_client, mock_db_session):
        """Test getting non-existent setting returns 404."""
        from app.services.setting import setting_service

        with patch.object(setting_service, "get_setting", return_value=None):
            response = admin_client.get("/settings/nonexistent.key")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_setting_non_admin_forbidden(self, non_admin_client):
        """Test non-admin user cannot get a specific setting."""
        response = non_admin_client.get("/settings/openai.api_key")
        assert response.status_code == 403
        assert "Admin privileges required" in response.json()["detail"]

    def test_get_setting_unauthenticated_forbidden(
        self, unauthenticated_client
    ):
        """Test unauthenticated user cannot get a specific setting."""
        response = unauthenticated_client.get("/settings/openai.api_key")
        assert response.status_code in [401, 403]


class TestUpdateSetting:
    """Test PUT /settings/{key} endpoint."""

    @pytest.mark.asyncio
    async def test_update_setting_admin_success(
        self, admin_client, mock_db_session, mock_setting
    ):
        """Test admin can successfully update a setting."""
        from app.services.setting import setting_service

        updated_setting = Setting(
            id=mock_setting.id,
            key=mock_setting.key,
            value="sk-newvalue",
            display_name=mock_setting.display_name,
            description=mock_setting.description,
            setting_type=mock_setting.setting_type,
            allowed_values=mock_setting.allowed_values,
            is_secret=mock_setting.is_secret,
            created_at=mock_setting.created_at,
            updated_at=datetime.now(timezone.utc),
        )

        with (
            patch.object(
                setting_service, "get_setting", return_value=mock_setting
            ),
            patch.object(
                setting_service,
                "create_or_update_setting",
                return_value=updated_setting,
            ),
            patch(
                "app.api.v1.endpoints.settings._refresh_settings_and_services"
            ) as mock_refresh,
        ):
            response = admin_client.put(
                "/settings/openai.api_key",
                json={"value": "sk-newvalue"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "openai.api_key"
        assert data["value"] == "sk-newvalue"
        # Verify cache refresh was called
        mock_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_setting_not_found(
        self, admin_client, mock_db_session
    ):
        """Test updating non-existent setting returns 404."""
        from app.services.setting import setting_service

        with patch.object(setting_service, "get_setting", return_value=None):
            response = admin_client.put(
                "/settings/nonexistent.key",
                json={"value": "newvalue"},
            )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_update_setting_non_admin_forbidden(self, non_admin_client):
        """Test non-admin user cannot update a setting."""
        response = non_admin_client.put(
            "/settings/openai.api_key",
            json={"value": "sk-newvalue"},
        )
        assert response.status_code == 403
        assert "Admin privileges required" in response.json()["detail"]

    def test_update_setting_unauthenticated_forbidden(
        self, unauthenticated_client
    ):
        """Test unauthenticated user cannot update a setting."""
        response = unauthenticated_client.put(
            "/settings/openai.api_key",
            json={"value": "sk-newvalue"},
        )
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_update_setting_with_all_fields(
        self, admin_client, mock_db_session, mock_setting
    ):
        """Test admin can update all setting fields."""
        from app.services.setting import setting_service

        updated_setting = Setting(
            id=mock_setting.id,
            key=mock_setting.key,
            value="sk-updated",
            display_name="Updated Display Name",
            description="Updated description",
            setting_type="string",
            allowed_values='["option1", "option2"]',
            is_secret=False,
            created_at=mock_setting.created_at,
            updated_at=datetime.now(timezone.utc),
        )

        with (
            patch.object(
                setting_service, "get_setting", return_value=mock_setting
            ),
            patch.object(
                setting_service,
                "create_or_update_setting",
                return_value=updated_setting,
            ),
            patch(
                "app.api.v1.endpoints.settings._refresh_settings_and_services"
            ),
        ):
            response = admin_client.put(
                "/settings/openai.api_key",
                json={
                    "value": "sk-updated",
                    "display_name": "Updated Display Name",
                    "description": "Updated description",
                    "setting_type": "string",
                    "allowed_values": ["option1", "option2"],
                    "is_secret": False,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["value"] == "sk-updated"
        assert data["display_name"] == "Updated Display Name"
        assert data["description"] == "Updated description"
        assert data["is_secret"] is False


class TestResetSetting:
    """Test POST /settings/{key}/reset endpoint."""

    @pytest.mark.asyncio
    async def test_reset_setting_admin_success(
        self, admin_client, mock_db_session, mock_setting
    ):
        """Test admin can successfully reset a setting to default."""
        from app.services.setting import setting_service

        reset_setting = Setting(
            id=mock_setting.id,
            key=mock_setting.key,
            value="default-value",
            display_name=mock_setting.display_name,
            description=mock_setting.description,
            setting_type=mock_setting.setting_type,
            allowed_values=mock_setting.allowed_values,
            is_secret=mock_setting.is_secret,
            created_at=mock_setting.created_at,
            updated_at=datetime.now(timezone.utc),
        )

        with (
            patch.object(
                setting_service,
                "reset_setting_to_default",
                return_value=reset_setting,
            ),
            patch(
                "app.api.v1.endpoints.settings._refresh_settings_and_services"
            ) as mock_refresh,
        ):
            response = admin_client.post("/settings/openai.api_key/reset")

        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "openai.api_key"
        assert data["value"] == "default-value"
        # Verify cache refresh was called
        mock_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_reset_setting_not_found(
        self, admin_client, mock_db_session
    ):
        """Test resetting non-existent setting returns 404."""
        from app.services.setting import setting_service

        with patch.object(
            setting_service, "reset_setting_to_default", return_value=None
        ):
            response = admin_client.post("/settings/nonexistent.key/reset")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_reset_setting_non_admin_forbidden(self, non_admin_client):
        """Test non-admin user cannot reset a setting."""
        response = non_admin_client.post("/settings/openai.api_key/reset")
        assert response.status_code == 403
        assert "Admin privileges required" in response.json()["detail"]

    def test_reset_setting_unauthenticated_forbidden(
        self, unauthenticated_client
    ):
        """Test unauthenticated user cannot reset a setting."""
        response = unauthenticated_client.post(
            "/settings/openai.api_key/reset"
        )
        assert response.status_code in [401, 403]


class TestSettingsSecurity:
    """Comprehensive security tests for all settings endpoints."""

    def test_all_endpoints_require_admin(self, non_admin_client):
        """Test that all settings endpoints reject non-admin users."""
        endpoints = [
            ("GET", "/settings"),
            ("GET", "/settings/test.key"),
            ("PUT", "/settings/test.key"),
            ("POST", "/settings/test.key/reset"),
        ]

        for method, endpoint in endpoints:
            if method == "GET":
                response = non_admin_client.get(endpoint)
            elif method == "PUT":
                response = non_admin_client.put(
                    endpoint, json={"value": "test"}
                )
            elif method == "POST":
                response = non_admin_client.post(endpoint)

            assert (
                response.status_code == 403
            ), f"{method} {endpoint} should return 403"
            assert "Admin privileges required" in response.json()["detail"]

    def test_all_endpoints_reject_unauthenticated(
        self, unauthenticated_client
    ):
        """Test that all settings endpoints reject unauthenticated users."""
        endpoints = [
            ("GET", "/settings"),
            ("GET", "/settings/test.key"),
            ("PUT", "/settings/test.key"),
            ("POST", "/settings/test.key/reset"),
        ]

        for method, endpoint in endpoints:
            if method == "GET":
                response = unauthenticated_client.get(endpoint)
            elif method == "PUT":
                response = unauthenticated_client.put(
                    endpoint, json={"value": "test"}
                )
            elif method == "POST":
                response = unauthenticated_client.post(endpoint)

            assert response.status_code in [
                401,
                403,
            ], f"{method} {endpoint} should return 401 or 403"

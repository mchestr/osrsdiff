"""Tests for startup service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.startup import StartupService


class TestStartupService:
    """Test cases for StartupService."""

    @pytest.fixture
    def startup_service(self):
        """Create a startup service instance."""
        return StartupService()

    @pytest.mark.asyncio
    async def test_run_database_migrations_success(self, startup_service):
        """Test successful database migration run."""
        with patch(
            "app.services.startup.run_migrations"
        ) as mock_run_migrations:
            await startup_service.run_database_migrations()

            mock_run_migrations.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_database_migrations_failure(self, startup_service):
        """Test database migration failure."""
        with patch(
            "app.services.startup.run_migrations"
        ) as mock_run_migrations:
            mock_run_migrations.side_effect = Exception("Migration failed")

            with pytest.raises(Exception) as exc_info:
                await startup_service.run_database_migrations()

            assert "Migration failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_admin_user_already_exists(
        self, startup_service, test_session
    ):
        """Test creating admin user when it already exists."""
        mock_user = MagicMock()
        mock_user.username = "admin"

        with patch(
            "app.services.startup.AsyncSessionLocal"
        ) as mock_session_local:
            mock_session_local.return_value.__aenter__.return_value = (
                test_session
            )

            with patch(
                "app.services.startup.settings_cache"
            ) as mock_settings_cache:
                mock_settings_cache.admin_username = "admin"

                with patch(
                    "app.services.startup.user_service"
                ) as mock_user_service:
                    mock_user_service.get_user_by_username = AsyncMock(
                        return_value=mock_user
                    )

                    await startup_service.create_admin_user()

                    mock_user_service.get_user_by_username.assert_called_once_with(
                        test_session, "admin"
                    )
                    mock_user_service.create_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_admin_user_new(self, startup_service, test_session):
        """Test creating a new admin user."""
        with patch(
            "app.services.startup.AsyncSessionLocal"
        ) as mock_session_local:
            mock_session_local.return_value.__aenter__.return_value = (
                test_session
            )

            with patch(
                "app.services.startup.settings_cache"
            ) as mock_settings_cache:
                mock_settings_cache.admin_username = "admin"
                mock_settings_cache.admin_password = "admin_password"
                mock_settings_cache.admin_email = "admin@example.com"

                with patch(
                    "app.services.startup.user_service"
                ) as mock_user_service:
                    mock_user_service.get_user_by_username = AsyncMock(
                        return_value=None
                    )
                    mock_admin_user = MagicMock()
                    mock_admin_user.id = 1
                    mock_admin_user.username = "admin"
                    mock_user_service.create_user = AsyncMock(
                        return_value=mock_admin_user
                    )

                    await startup_service.create_admin_user()

                    mock_user_service.create_user.assert_called_once_with(
                        db=test_session,
                        username="admin",
                        password="admin_password",
                        email="admin@example.com",
                        is_admin=True,
                    )

    @pytest.mark.asyncio
    async def test_initialize_settings_success(
        self, startup_service, test_session
    ):
        """Test successful settings initialization."""
        with patch(
            "app.services.startup.AsyncSessionLocal"
        ) as mock_session_local:
            mock_session_local.return_value.__aenter__.return_value = (
                test_session
            )

            with patch(
                "app.services.startup.setting_service"
            ) as mock_setting_service:
                mock_setting_service.initialize_from_config = AsyncMock()

                await startup_service.initialize_settings()

                mock_setting_service.initialize_from_config.assert_called_once_with(
                    test_session
                )

    @pytest.mark.asyncio
    async def test_initialize_settings_failure(
        self, startup_service, test_session
    ):
        """Test settings initialization failure."""
        with patch(
            "app.services.startup.AsyncSessionLocal"
        ) as mock_session_local:
            mock_session_local.return_value.__aenter__.return_value = (
                test_session
            )

            with patch(
                "app.services.startup.setting_service"
            ) as mock_setting_service:
                mock_setting_service.initialize_from_config = AsyncMock(
                    side_effect=Exception("Init failed")
                )

                with pytest.raises(Exception) as exc_info:
                    await startup_service.initialize_settings()

                assert "Init failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_load_settings_cache_success(self, startup_service):
        """Test successful settings cache load."""
        with patch(
            "app.services.startup.settings_cache"
        ) as mock_settings_cache:
            mock_settings_cache.load_from_database = AsyncMock()

            await startup_service.load_settings_cache()

            mock_settings_cache.load_from_database.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_settings_cache_failure(self, startup_service):
        """Test settings cache load failure."""
        with patch(
            "app.services.startup.settings_cache"
        ) as mock_settings_cache:
            mock_settings_cache.load_from_database = AsyncMock(
                side_effect=Exception("Load failed")
            )

            with pytest.raises(Exception) as exc_info:
                await startup_service.load_settings_cache()

            assert "Load failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_startup_deprecated(self, startup_service):
        """Test that startup method is deprecated and calls all methods."""
        with patch.object(
            startup_service, "run_database_migrations"
        ) as mock_migrations:
            with patch.object(
                startup_service, "initialize_settings"
            ) as mock_init_settings:
                with patch.object(
                    startup_service, "load_settings_cache"
                ) as mock_load_cache:
                    with patch.object(
                        startup_service, "create_admin_user"
                    ) as mock_create_admin:
                        await startup_service.startup()

                        mock_migrations.assert_called_once()
                        mock_init_settings.assert_called_once()
                        mock_load_cache.assert_called_once()
                        mock_create_admin.assert_called_once()

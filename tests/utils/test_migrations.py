"""Tests for migration utilities."""

import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.utils.migrations import run_migrations


class TestRunMigrations:
    """Test cases for run_migrations function."""

    def test_run_migrations_success(self, tmp_path, monkeypatch):
        """Test successful migration run."""
        # Create a temporary alembic.ini file
        project_root = tmp_path
        alembic_ini = project_root / "alembic.ini"
        alembic_ini.write_text("[alembic]\n")

        # Mock Path(__file__) to return our temp path structure
        mock_file_path = MagicMock()
        mock_file_path.parent.parent.parent = project_root

        with patch("app.utils.migrations.Path") as mock_path_class:
            # Make Path(__file__) return our mock
            mock_path_class.return_value = mock_file_path

            with patch("app.utils.migrations.Config") as mock_config_class:
                mock_config = MagicMock()
                mock_config_class.return_value = mock_config

                with patch(
                    "app.utils.migrations.command.upgrade"
                ) as mock_upgrade:
                    with patch(
                        "app.utils.migrations.settings"
                    ) as mock_settings:
                        mock_settings.database.url = "sqlite:///test.db"

                        # Now run migrations
                        run_migrations()

                        mock_config_class.assert_called_once()
                        mock_config.set_main_option.assert_called_once_with(
                            "sqlalchemy.url", "sqlite:///test.db"
                        )
                        mock_upgrade.assert_called_once_with(
                            mock_config, "head"
                        )

    def test_run_migrations_missing_alembic_ini(self, tmp_path):
        """Test migration run with missing alembic.ini."""
        project_root = tmp_path

        with patch("app.utils.migrations.Path") as mock_path:
            # Make sure alembic.ini doesn't exist
            alembic_ini_path = project_root / "alembic.ini"
            assert not alembic_ini_path.exists()

            mock_file_path = MagicMock()
            mock_file_path.parent.parent.parent = project_root
            mock_path.return_value = mock_file_path

            with pytest.raises(FileNotFoundError) as exc_info:
                run_migrations()

            assert "Alembic config file not found" in str(exc_info.value)

    def test_run_migrations_failure(self, tmp_path):
        """Test migration run with failure."""
        project_root = tmp_path
        alembic_ini = project_root / "alembic.ini"
        alembic_ini.write_text("[alembic]\n")

        with patch("app.utils.migrations.Path") as mock_path:
            mock_file_path = MagicMock()
            mock_file_path.parent.parent.parent = project_root
            mock_path.return_value = mock_file_path

            with patch("app.utils.migrations.Config") as mock_config_class:
                mock_config = MagicMock()
                mock_config_class.return_value = mock_config

                with patch(
                    "app.utils.migrations.command.upgrade"
                ) as mock_upgrade:
                    mock_upgrade.side_effect = Exception("Migration failed")

                    with patch(
                        "app.utils.migrations.settings"
                    ) as mock_settings:
                        mock_settings.database.url = "sqlite:///test.db"

                        with pytest.raises(Exception) as exc_info:
                            run_migrations()

                        assert "Migration failed" in str(exc_info.value)

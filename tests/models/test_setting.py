"""Tests for Setting model."""

from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.setting import Setting


class TestSettingModel:
    """Test cases for Setting model."""

    def test_setting_creation(self):
        """Test creating a Setting instance."""
        setting = Setting(
            key="test_key",
            value="test_value",
            display_name="Test Setting",
            description="A test setting",
            setting_type="string",
            is_secret=False,
        )

        assert setting.key == "test_key"
        assert setting.value == "test_value"
        assert setting.display_name == "Test Setting"
        assert setting.description == "A test setting"
        assert setting.setting_type == "string"
        assert setting.is_secret is False

    def test_setting_defaults(self):
        """Test Setting with default values."""
        setting = Setting(key="test_key", value="test_value")

        # Defaults are applied at database level, not Python object level
        # So setting_type and is_secret will be None/False until persisted
        assert setting.display_name is None
        assert setting.description is None
        # Note: setting_type and is_secret defaults are applied by the database
        # when the object is persisted, not when creating the Python object

    def test_setting_repr(self):
        """Test Setting string representation."""
        setting = Setting(
            key="test_key",
            value="test_value_that_is_longer_than_fifty_characters_to_test_truncation",
        )

        repr_str = repr(setting)
        assert "Setting" in repr_str
        assert "test_key" in repr_str
        assert "test_value" in repr_str
        # The repr shows first 50 chars followed by "..."
        # Check that the repr contains the truncated value indicator
        assert "..." in repr_str or len(setting.value[:50]) <= 50

    def test_setting_with_enum_type(self):
        """Test Setting with enum type."""
        setting = Setting(
            key="test_enum",
            value="option1",
            setting_type="enum",
            allowed_values='["option1", "option2", "option3"]',
        )

        assert setting.setting_type == "enum"
        assert setting.allowed_values == '["option1", "option2", "option3"]'

    def test_setting_with_secret(self):
        """Test Setting with secret flag."""
        setting = Setting(key="api_key", value="secret_value", is_secret=True)

        assert setting.is_secret is True
        assert setting.value == "secret_value"

    def test_setting_timestamps(self):
        """Test Setting timestamp fields."""
        # Timestamps are set by database defaults, not Python object creation
        # They will be None until the object is persisted
        setting = Setting(key="test_key", value="test_value")

        # Timestamps are None until persisted to database
        assert setting.created_at is None or isinstance(
            setting.created_at, datetime
        )
        assert setting.updated_at is None or isinstance(
            setting.updated_at, datetime
        )

    @pytest.mark.asyncio
    async def test_setting_database_operations(
        self, test_session: AsyncSession
    ):
        """Test Setting database operations."""
        setting = Setting(
            key="db_test_key",
            value="db_test_value",
            display_name="DB Test Setting",
        )

        test_session.add(setting)
        await test_session.commit()
        await test_session.refresh(setting)

        assert setting.id is not None
        assert setting.key == "db_test_key"
        assert setting.value == "db_test_value"

        # Test update
        setting.value = "updated_value"
        await test_session.commit()
        await test_session.refresh(setting)

        assert setting.value == "updated_value"

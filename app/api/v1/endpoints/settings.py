import json
import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_utils import require_admin
from app.exceptions import NotFoundError
from app.models.base import get_db_session
from app.services.auth import auth_service
from app.services.setting import setting_service
from app.services.settings_cache import settings_cache
from app.services.token_blacklist import token_blacklist_service

logger = logging.getLogger(__name__)


async def _refresh_settings_and_services() -> None:
    """Refresh settings cache and update all dependent services."""
    # Reload settings from database
    await settings_cache.load_from_database()

    # Refresh services that depend on settings
    auth_service._refresh_settings()
    token_blacklist_service._refresh_settings()

    logger.info("Settings cache and dependent services refreshed")


def _parse_allowed_values(allowed_values_str: str | None) -> List[str] | None:
    """Parse allowed_values JSON string to list."""
    if not allowed_values_str:
        return None
    try:
        parsed = json.loads(allowed_values_str)
        if isinstance(parsed, list) and all(
            isinstance(item, str) for item in parsed
        ):
            return parsed
        return None
    except (json.JSONDecodeError, TypeError):
        logger.warning(f"Failed to parse allowed_values: {allowed_values_str}")
        return None


# Request/Response models
class SettingResponse(BaseModel):
    """Response model for a single setting."""

    id: int = Field(description="Setting ID")
    key: str = Field(description="Setting key")
    value: str = Field(description="Setting value")
    display_name: str | None = Field(
        default=None, description="Friendly display name for the setting"
    )
    description: str | None = Field(
        default=None, description="Setting description"
    )
    setting_type: str = Field(
        default="string",
        description="Setting type (string, number, boolean, enum)",
    )
    allowed_values: List[str] | None = Field(
        default=None, description="Allowed values for enum type settings"
    )
    is_secret: bool = Field(
        default=False,
        description="Whether the setting value should be obfuscated in UI",
    )
    created_at: str = Field(description="Creation timestamp")
    updated_at: str = Field(description="Last update timestamp")


def _setting_to_response(setting: Any) -> SettingResponse:
    """Convert a Setting model to SettingResponse."""
    return SettingResponse(
        id=setting.id,
        key=setting.key,
        value=setting.value,
        display_name=setting.display_name,
        description=setting.description,
        setting_type=setting.setting_type or "string",
        allowed_values=_parse_allowed_values(setting.allowed_values),
        is_secret=setting.is_secret,
        created_at=setting.created_at.isoformat(),
        updated_at=setting.updated_at.isoformat(),
    )


class SettingListResponse(BaseModel):
    """Response model for list of settings."""

    settings: List[SettingResponse] = Field(description="List of settings")


class SettingUpdateRequest(BaseModel):
    """Request model for updating a setting."""

    value: str = Field(description="Setting value")
    display_name: str | None = Field(
        default=None, description="Friendly display name for the setting"
    )
    description: str | None = Field(
        default=None, description="Setting description"
    )
    setting_type: str | None = Field(
        default=None,
        description="Setting type (string, number, boolean, enum)",
    )
    allowed_values: List[str] | None = Field(
        default=None, description="Allowed values for enum type settings"
    )
    is_secret: bool | None = Field(
        default=None,
        description="Whether the setting value should be obfuscated in UI",
    )


class SettingDictResponse(BaseModel):
    """Response model for settings as dictionary."""

    settings: Dict[str, str] = Field(description="Settings as key-value pairs")


# Router
router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingListResponse)
async def get_all_settings(
    db_session: AsyncSession = Depends(get_db_session),
    current_user: Dict[str, Any] = Depends(require_admin),
) -> SettingListResponse:
    """
    Get all settings.

    Returns all application settings. Admin only.

    Args:
        db_session: Database session dependency
        current_user: Authenticated admin user information

    Returns:
        SettingListResponse: List of all settings

    Raises:
        403 Forbidden: User is not an admin
    """
    settings = await setting_service.get_all_settings(db_session)
    return SettingListResponse(
        settings=[_setting_to_response(setting) for setting in settings]
    )


@router.get("/dict", response_model=SettingDictResponse)
async def get_all_settings_dict(
    db_session: AsyncSession = Depends(get_db_session),
    current_user: Dict[str, Any] = Depends(require_admin),
) -> SettingDictResponse:
    """
    Get all settings as a dictionary.

    Returns all settings as key-value pairs. Admin only.

    Args:
        db_session: Database session dependency
        current_user: Authenticated admin user information

    Returns:
        SettingDictResponse: Settings as dictionary

    Raises:
        403 Forbidden: User is not an admin
    """
    settings_dict = await setting_service.get_all_settings_dict(db_session)
    return SettingDictResponse(settings=settings_dict)


@router.get("/{key}", response_model=SettingResponse)
async def get_setting(
    key: str,
    db_session: AsyncSession = Depends(get_db_session),
    current_user: Dict[str, Any] = Depends(require_admin),
) -> SettingResponse:
    """
    Get a specific setting by key.

    Returns a single setting by its key. Admin only.

    Args:
        key: Setting key
        db_session: Database session dependency
        current_user: Authenticated admin user information

    Returns:
        SettingResponse: The requested setting

    Raises:
        403 Forbidden: User is not an admin
        404 Not Found: Setting not found
    """
    setting = await setting_service.get_setting(db_session, key)
    if not setting:
        raise NotFoundError(f"Setting '{key}' not found")

    return _setting_to_response(setting)


@router.put("/{key}", response_model=SettingResponse)
async def update_setting(
    key: str,
    request: SettingUpdateRequest,
    db_session: AsyncSession = Depends(get_db_session),
    current_user: Dict[str, Any] = Depends(require_admin),
) -> SettingResponse:
    """
    Update an existing setting.

    Updates an existing setting's value and/or description. Admin only.

    Args:
        key: Setting key
        request: Setting update request
        db_session: Database session dependency
        current_user: Authenticated admin user information

    Returns:
        SettingResponse: The updated setting

    Raises:
        403 Forbidden: User is not an admin
        404 Not Found: Setting not found
    """
    # Check if setting exists
    existing = await setting_service.get_setting(db_session, key)
    if not existing:
        raise NotFoundError(f"Setting '{key}' not found")

    # Convert allowed_values list to JSON string if provided
    allowed_values_str = None
    if request.allowed_values:
        allowed_values_str = json.dumps(request.allowed_values)

    setting = await setting_service.create_or_update_setting(
        db_session,
        key,
        request.value,
        request.description,
        request.display_name,
        request.setting_type,
        allowed_values_str,
        request.is_secret,
    )

    # Refresh settings cache and dependent services
    await _refresh_settings_and_services()

    return _setting_to_response(setting)


@router.post("/{key}/reset", response_model=SettingResponse)
async def reset_setting(
    key: str,
    db_session: AsyncSession = Depends(get_db_session),
    current_user: Dict[str, Any] = Depends(require_admin),
) -> SettingResponse:
    """
    Reset a setting to its default value from config.py.

    Resets a setting to its default value as defined in config.py. Admin only.

    Args:
        key: Setting key
        db_session: Database session dependency
        current_user: Authenticated admin user information

    Returns:
        SettingResponse: The reset setting

    Raises:
        403 Forbidden: User is not an admin
        404 Not Found: Setting not found or no default value available
    """
    setting = await setting_service.reset_setting_to_default(db_session, key)
    if not setting:
        raise NotFoundError(
            f"Setting '{key}' not found or no default value available"
        )

    # Refresh settings cache and dependent services
    await _refresh_settings_and_services()

    return _setting_to_response(setting)

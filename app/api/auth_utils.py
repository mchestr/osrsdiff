"""Authentication API endpoints and dependencies."""

from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
    OAuth2PasswordBearer,
)
from pydantic import BaseModel

from app.services.auth import auth_service


# Pydantic models for request/response
class TokenResponse(BaseModel):
    """Token response model."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefreshRequest(BaseModel):
    """Token refresh request model."""

    refresh_token: str


class TokenRefreshResponse(BaseModel):
    """Token refresh response model."""

    access_token: str
    token_type: str = "bearer"


# FastAPI security schemes
security = HTTPBearer()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
) -> Dict[str, Any]:
    """
    FastAPI dependency to get current authenticated user from JWT token.

    Args:
        token: JWT access token from OAuth2 scheme

    Returns:
        The decoded token payload containing user information

    Raises:
        HTTPException: If token is invalid or expired
    """
    return await auth_service.validate_token(token, token_type="access")


async def get_current_user_bearer(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:
    """
    FastAPI dependency to get current authenticated user from Bearer token.

    Args:
        credentials: HTTP Bearer token credentials

    Returns:
        The decoded token payload containing user information

    Raises:
        HTTPException: If token is invalid or expired
    """
    token = credentials.credentials
    return await auth_service.validate_token(token, token_type="access")


async def get_optional_current_user(
    token: Optional[str] = Depends(
        OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)
    )
) -> Optional[Dict[str, Any]]:
    """
    FastAPI dependency to optionally get current authenticated user.

    Args:
        token: Optional JWT access token

    Returns:
        The decoded token payload if valid token provided, None otherwise
    """
    if token is None:
        return None

    try:
        return await auth_service.validate_token(token, token_type="access")
    except HTTPException:
        return None


def require_auth(
    user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    FastAPI dependency that requires authentication.

    Args:
        user: Current authenticated user from get_current_user dependency

    Returns:
        The authenticated user data
    """
    return user


def optional_auth(
    user: Optional[Dict[str, Any]] = Depends(get_optional_current_user),
) -> Optional[Dict[str, Any]]:
    """
    FastAPI dependency for optional authentication.

    Args:
        user: Optional current authenticated user

    Returns:
        The authenticated user data if available, None otherwise
    """
    return user

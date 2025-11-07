from typing import Any, Dict

from fastapi import APIRouter, Depends
from fastapi.security import (
    HTTPAuthorizationCredentials,
    OAuth2PasswordRequestForm,
)
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_utils import (
    get_current_user_bearer,
    require_auth,
    security,
)
from app.exceptions import UnauthorizedError
from app.models.base import get_db_session
from app.services.auth import auth_service


# Request/Response models
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


class UserResponse(BaseModel):
    """User response model."""

    username: str
    user_id: int


# Router
router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """
    Login endpoint to generate JWT tokens.

    Compatible with OAuth2 password flow for OpenAPI docs integration.
    """
    # Authenticate user against database
    user = await auth_service.authenticate_user(
        db, form_data.username, form_data.password
    )

    if not user:
        raise UnauthorizedError("Invalid username or password")

    user_data = auth_service.create_user_token_data(user)
    tokens = auth_service.create_token_pair(user_data)
    return TokenResponse(**tokens)


@router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh_token(request: TokenRefreshRequest) -> TokenRefreshResponse:
    """
    Refresh access token using refresh token.
    """
    try:
        new_access_token = await auth_service.refresh_access_token(
            request.refresh_token
        )
        return TokenRefreshResponse(
            access_token=new_access_token, token_type="bearer"
        )
    except UnauthorizedError:
        raise
    except Exception as e:
        raise UnauthorizedError("Invalid refresh token", detail=str(e))


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: Dict[str, Any] = Depends(require_auth),
) -> UserResponse:
    """
    Get current authenticated user information.

    This endpoint demonstrates how to use the authentication dependency.
    """
    return UserResponse(
        username=current_user["username"], user_id=current_user["user_id"]
    )


@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: Dict[str, Any] = Depends(get_current_user_bearer),
) -> Dict[str, str]:
    """
    Logout endpoint that blacklists the current access token.
    """
    # Blacklist the current token
    token = credentials.credentials
    await auth_service.logout_token(token)

    return {"message": "Successfully logged out"}

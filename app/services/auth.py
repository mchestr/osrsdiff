from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import JWTError, jwt  # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import UnauthorizedError
from app.models.user import User
from app.services.settings_cache import settings_cache
from app.services.token_blacklist import token_blacklist_service
from app.services.user import user_service


class AuthService:
    """JWT authentication service for token generation and validation."""

    def __init__(self) -> None:
        """Initialize the authentication service."""
        self._refresh_settings()

    def _refresh_settings(self) -> None:
        """Refresh settings from cache."""
        self.secret_key = settings_cache.jwt_secret_key
        self.algorithm = settings_cache.jwt_algorithm
        self.access_token_expire_minutes = (
            settings_cache.jwt_access_token_expire_minutes
        )
        self.refresh_token_expire_days = (
            settings_cache.jwt_refresh_token_expire_days
        )

    async def authenticate_user(
        self, db: AsyncSession, username: str, password: str
    ) -> Optional[User]:
        """Authenticate a user with username and password."""
        return await user_service.authenticate_user(db, username, password)

    def create_user_token_data(self, user: User) -> Dict[str, Any]:
        """Create token data from user object."""
        return {
            "sub": str(user.id),
            "username": user.username,
            "user_id": user.id,
            "is_admin": user.is_admin,
        }

    def create_access_token(self, data: Dict[str, Any]) -> str:
        """
        Create a JWT access token.

        Args:
            data: The payload data to encode in the token

        Returns:
            The encoded JWT token string
        """
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=self.access_token_expire_minutes
        )
        to_encode.update({"exp": expire, "type": "access"})

        encoded_token: str = jwt.encode(
            to_encode, self.secret_key, algorithm=self.algorithm
        )
        return encoded_token

    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """
        Create a JWT refresh token.

        Args:
            data: The payload data to encode in the token

        Returns:
            The encoded JWT refresh token string
        """
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(
            days=self.refresh_token_expire_days
        )
        to_encode.update({"exp": expire, "type": "refresh"})

        encoded_token: str = jwt.encode(
            to_encode, self.secret_key, algorithm=self.algorithm
        )
        return encoded_token

    def create_token_pair(self, user_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Create both access and refresh tokens.

        Args:
            user_data: The user data to encode in the tokens

        Returns:
            Dictionary containing access_token and refresh_token
        """
        access_token = self.create_access_token(user_data)
        refresh_token = self.create_refresh_token(user_data)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    async def validate_token(
        self, token: str, token_type: str = "access"
    ) -> Dict[str, Any]:
        """
        Validate and decode a JWT token.

        Args:
            token: The JWT token to validate
            token_type: Expected token type ("access" or "refresh")

        Returns:
            The decoded token payload

        Raises:
            UnauthorizedError: If token is invalid, expired, or wrong type
        """
        credentials_exception = UnauthorizedError(
            "Could not validate credentials"
        )

        try:
            # Check if token is blacklisted first
            if await token_blacklist_service.is_token_blacklisted(token):
                raise UnauthorizedError("Token has been revoked")

            payload: Dict[str, Any] = jwt.decode(
                token, self.secret_key, algorithms=[self.algorithm]
            )

            # Check if token has expired
            exp = payload.get("exp")
            if exp is None:
                raise credentials_exception

            if datetime.now(timezone.utc) > datetime.fromtimestamp(
                exp, tz=timezone.utc
            ):
                raise UnauthorizedError("Token has expired")

            # Check token type
            if payload.get("type") != token_type:
                raise UnauthorizedError(
                    f"Invalid token type. Expected {token_type}"
                )

            return payload

        except JWTError:
            raise credentials_exception

    async def refresh_access_token(self, refresh_token: str) -> str:
        """
        Create a new access token using a valid refresh token.

        Args:
            refresh_token: The refresh token to use

        Returns:
            New access token

        Raises:
            HTTPException: If refresh token is invalid or expired
        """
        payload = await self.validate_token(
            refresh_token, token_type="refresh"
        )

        # Extract user data (excluding token metadata)
        user_data = {
            k: v for k, v in payload.items() if k not in ["exp", "type", "iat"]
        }

        return self.create_access_token(user_data)

    async def logout_token(self, token: str) -> None:
        """
        Logout by blacklisting the provided token.

        Args:
            token: The access token to blacklist
        """
        await token_blacklist_service.blacklist_token(token)


# Global auth service instance
auth_service = AuthService()

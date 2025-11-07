from datetime import datetime, timezone
from typing import Optional

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserService:
    """Service for user management operations."""

    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        # Convert password to bytes and hash it
        password_bytes = password.encode("utf-8")
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode("utf-8")

    def verify_password(
        self, plain_password: str, hashed_password: str
    ) -> bool:
        """Verify a password against its hash."""
        # Convert both to bytes for bcrypt
        password_bytes = plain_password.encode("utf-8")
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hashed_bytes)

    async def get_user_by_username(
        self, db: AsyncSession, username: str
    ) -> Optional[User]:
        """Get a user by username."""
        result = await db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_user_by_id(
        self, db: AsyncSession, user_id: int
    ) -> Optional[User]:
        """Get a user by ID."""
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def create_user(
        self,
        db: AsyncSession,
        username: str,
        password: str,
        email: Optional[str] = None,
        is_admin: bool = False,
    ) -> User:
        """Create a new user."""
        hashed_password = self.hash_password(password)

        user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            is_admin=is_admin,
            is_active=True,
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    async def authenticate_user(
        self, db: AsyncSession, username: str, password: str
    ) -> Optional[User]:
        """Authenticate a user with username and password."""
        user = await self.get_user_by_username(db, username)
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        if not user.is_active:
            return None

        # Update last login
        user.last_login = datetime.now(timezone.utc)
        await db.commit()

        return user

    async def update_user_last_login(
        self, db: AsyncSession, user_id: int
    ) -> None:
        """Update user's last login timestamp."""
        user = await self.get_user_by_id(db, user_id)
        if user:
            user.last_login = datetime.now(timezone.utc)
            await db.commit()


# Global user service instance
user_service = UserService()

"""
Refresh token service for secure token rotation and revocation.
"""
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from app.models import RefreshToken, User
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("refresh_token_service")


class RefreshTokenService:
    """Service for managing refresh tokens with rotation and revocation."""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _hash_token(token: str) -> str:
        """Hash a refresh token using SHA-256."""
        return hashlib.sha256(token.encode()).hexdigest()

    async def create_token(self, user_id: str) -> Tuple[str, RefreshToken]:
        """
        Create a new refresh token for a user.

        Args:
            user_id: ID of the user

        Returns:
            Tuple of (plain_token, RefreshToken model instance)
        """
        from app.core.security import create_refresh_token
        
        # Generate the JWT refresh token
        plain_token = create_refresh_token(data={"sub": user_id})
        
        # Hash it for storage
        token_hash = self._hash_token(plain_token)
        
        # Calculate expiration
        expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        # Create database record
        refresh_token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            revoked=False,
        )
        
        self.db.add(refresh_token)
        await self.db.flush()
        
        logger.info(f"Created refresh token for user {user_id}, expires {expires_at}")
        
        return plain_token, refresh_token

    async def verify_token(self, plain_token: str) -> Optional[RefreshToken]:
        """
        Verify a refresh token is valid and not revoked.

        Args:
            plain_token: The plain refresh token string

        Returns:
            RefreshToken instance if valid, None otherwise
        """
        token_hash = self._hash_token(plain_token)
        
        # Find the token
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked == False,
                RefreshToken.expires_at > datetime.utcnow(),
            )
        )
        refresh_token = result.scalar_one_or_none()
        
        if not refresh_token:
            logger.warning(f"Invalid or expired refresh token attempted")
            return None
        
        return refresh_token

    async def rotate_token(self, old_token: str) -> Optional[Tuple[str, RefreshToken]]:
        """
        Rotate a refresh token: revoke the old one and issue a new one.

        This implements secure token rotation to prevent token replay attacks.

        Args:
            old_token: The current refresh token to rotate

        Returns:
            Tuple of (new_plain_token, new_RefreshToken) if successful, None if old token invalid
        """
        # Verify the old token
        old_refresh_token = await self.verify_token(old_token)
        
        if not old_refresh_token:
            logger.warning("Attempted to rotate invalid refresh token")
            return None
        
        # Revoke the old token
        old_refresh_token.revoked = True
        old_refresh_token.revoked_at = datetime.utcnow()
        
        # Create a new token
        new_plain_token, new_refresh_token = await self.create_token(old_refresh_token.user_id)
        
        # Link old token to new token for audit trail
        old_refresh_token.replaced_by = new_refresh_token.id
        
        await self.db.flush()
        
        logger.info(f"Rotated refresh token for user {old_refresh_token.user_id}")
        
        return new_plain_token, new_refresh_token

    async def revoke_token(self, token_hash: str) -> bool:
        """
        Revoke a specific refresh token.

        Args:
            token_hash: Hash of the token to revoke

        Returns:
            True if token was revoked, False if not found
        """
        result = await self.db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked == False,
            )
            .values(
                revoked=True,
                revoked_at=datetime.utcnow(),
            )
        )
        
        if result.rowcount > 0:
            logger.info(f"Revoked refresh token {token_hash[:16]}...")
            return True
        
        return False

    async def revoke_all_user_tokens(self, user_id: str) -> int:
        """
        Revoke all refresh tokens for a user (e.g., on logout or password change).

        Args:
            user_id: ID of the user

        Returns:
            Number of tokens revoked
        """
        result = await self.db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked == False,
            )
            .values(
                revoked=True,
                revoked_at=datetime.utcnow(),
            )
        )
        
        count = result.rowcount
        if count > 0:
            logger.info(f"Revoked {count} refresh tokens for user {user_id}")
        
        return count

    async def cleanup_expired_tokens(self, days_old: int = 30) -> int:
        """
        Clean up expired and revoked tokens older than specified days.

        Args:
            days_old: Delete tokens older than this many days

        Returns:
            Number of tokens deleted
        """
        cutoff = datetime.utcnow() - timedelta(days=days_old)
        
        result = await self.db.execute(
            delete(RefreshToken).where(
                RefreshToken.expires_at < cutoff,
                RefreshToken.revoked == True,
            )
        )
        
        count = result.rowcount
        if count > 0:
            logger.info(f"Cleaned up {count} expired refresh tokens")
        
        return count

"""
Audit logging service for security-sensitive operations.
"""
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import AuditLog
from app.core.logging import get_logger

logger = get_logger("audit_service")


class AuditService:
    """Service for logging security-sensitive operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        action: str,
        entity_type: str,
        entity_id: str,
        user_id: Optional[str] = None,
        changes: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """
        Create an audit log entry.

        Args:
            action: Action performed (e.g., "login", "logout", "password_reset", "create", "update", "delete")
            entity_type: Type of entity affected (e.g., "user", "student", "call", "campaign")
            entity_id: ID of the affected entity
            user_id: ID of the user performing the action (if authenticated)
            changes: Optional dictionary of changes (before/after values)
            ip_address: Client IP address
            user_agent: Client user agent string

        Returns:
            Created AuditLog instance
        """
        audit_log = AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(audit_log)
        await self.db.flush()
        
        logger.info(
            f"Audit: {action} on {entity_type}:{entity_id} by user:{user_id or 'anonymous'}",
            extra={
                "action": action,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "user_id": user_id,
            }
        )
        
        return audit_log

    async def log_authentication(
        self,
        user_id: str,
        action: str = "login",
        success: bool = True,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """Log authentication events (login, logout, failed login)."""
        return await self.log(
            action=action if success else f"{action}_failed",
            entity_type="user",
            entity_id=user_id,
            user_id=user_id,
            changes={"success": success},
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def log_password_reset(
        self,
        user_id: str,
        admin_user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """Log password reset events."""
        return await self.log(
            action="password_reset",
            entity_type="user",
            entity_id=user_id,
            user_id=admin_user_id or user_id,
            changes={"reset_by": "admin" if admin_user_id else "self"},
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def log_admin_action(
        self,
        admin_user_id: str,
        action: str,
        entity_type: str,
        entity_id: str,
        changes: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """Log admin actions."""
        return await self.log(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=admin_user_id,
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent,
        )

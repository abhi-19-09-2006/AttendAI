"""
Audit log model.
"""
from datetime import datetime
from typing import Optional
from uuid import uuid4
from sqlalchemy import String, DateTime, ForeignKey, Text, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class AuditLog(Base):
    """Audit log for tracking sensitive operations."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index('ix_audit_logs_user_id', 'user_id'),
        Index('ix_audit_logs_action', 'action'),
        Index('ix_audit_logs_entity_type', 'entity_type'),
        Index('ix_audit_logs_created_at', 'created_at'),
    )

    # Primary Key
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Foreign Keys
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)

    # Action Details
    action: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "create", "update", "delete", "login"
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "student", "call", "user"
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)

    # Change Data
    changes: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Before/after values

    # Request Context
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # IPv6 max length
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action={self.action}, entity_type={self.entity_type})>"

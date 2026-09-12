"""
Follow-up task model.
"""
from datetime import datetime, date
from typing import Optional
from uuid import uuid4
from sqlalchemy import String, Date, DateTime, ForeignKey, Enum as SQLEnum, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.enums import FollowUpType, FollowUpPriority, FollowUpStatus


class FollowUp(Base):
    """Follow-up task model."""

    __tablename__ = "followups"
    __table_args__ = (
        Index('ix_followups_status', 'status'),
        Index('ix_followups_priority', 'priority'),
        Index('ix_followups_due_date', 'due_date'),
        Index('ix_followups_assigned_to', 'assigned_to'),
    )

    # Primary Key
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Foreign Keys
    absence_report_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("absence_reports.id"), nullable=True)
    call_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("calls.id"), nullable=True)
    student_id: Mapped[str] = mapped_column(String(36), ForeignKey("students.id"), nullable=False)
    assigned_to: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)

    # Task Details
    type: Mapped[FollowUpType] = mapped_column(SQLEnum(FollowUpType), nullable=False)
    priority: Mapped[FollowUpPriority] = mapped_column(
        SQLEnum(FollowUpPriority),
        default=FollowUpPriority.MEDIUM,
        nullable=False
    )
    status: Mapped[FollowUpStatus] = mapped_column(
        SQLEnum(FollowUpStatus),
        default=FollowUpStatus.PENDING,
        nullable=False
    )

    # Scheduling
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Content
    description: Mapped[str] = mapped_column(Text, nullable=False)
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Completion
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    absence_report = relationship("AbsenceReport", back_populates="followups")
    call = relationship("Call", back_populates="followups")
    student = relationship("Student", back_populates="followups")
    assigned_to_user = relationship("User", back_populates="assigned_followups")

    def __repr__(self) -> str:
        return f"<FollowUp(id={self.id}, type={self.type}, status={self.status}, priority={self.priority})>"

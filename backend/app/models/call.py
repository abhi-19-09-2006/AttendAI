"""
Call and CallAttempt models.
"""
from datetime import datetime
from typing import Optional
from uuid import uuid4
from sqlalchemy import String, DateTime, ForeignKey, Enum as SQLEnum, Integer, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.enums import CallStatus


class Call(Base):
    """Call record model."""

    __tablename__ = "calls"
    __table_args__ = (
        Index('ix_calls_status', 'status'),
        Index('ix_calls_scheduled_time', 'scheduled_time'),
        Index('ix_calls_student_id', 'student_id'),
    )

    # Primary Key
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Foreign Keys
    campaign_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("call_campaigns.id"), nullable=True)
    student_id: Mapped[str] = mapped_column(String(36), ForeignKey("students.id"), nullable=False)
    parent_id: Mapped[str] = mapped_column(String(36), ForeignKey("parents.id"), nullable=False)
    attendance_id: Mapped[str] = mapped_column(String(36), ForeignKey("attendance.id"), nullable=False)

    # Call Details
    status: Mapped[CallStatus] = mapped_column(SQLEnum(CallStatus), default=CallStatus.PENDING, nullable=False)
    phone_number_called: Mapped[str] = mapped_column(String(20), nullable=False)

    # Vapi Integration
    vapi_call_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

    # Scheduling & Timing
    scheduled_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    initiated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    answered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Retry Management
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    campaign = relationship("CallCampaign", back_populates="calls")
    student = relationship("Student", back_populates="calls")
    parent = relationship("Parent", back_populates="calls")
    attendance = relationship("Attendance", back_populates="calls")
    attempts = relationship("CallAttempt", back_populates="call", cascade="all, delete-orphan")
    absence_report = relationship("AbsenceReport", back_populates="call", uselist=False)
    followups = relationship("FollowUp", back_populates="call")

    def __repr__(self) -> str:
        return f"<Call(id={self.id}, status={self.status}, student_id={self.student_id})>"


class CallAttempt(Base):
    """Individual call attempt record."""

    __tablename__ = "call_attempts"
    __table_args__ = (
        Index('ix_call_attempts_call_id', 'call_id'),
    )

    # Primary Key
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Foreign Keys
    call_id: Mapped[str] = mapped_column(String(36), ForeignKey("calls.id"), nullable=False)

    # Attempt Details
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[CallStatus] = mapped_column(SQLEnum(CallStatus), nullable=False)

    # Vapi Integration
    vapi_call_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Timing
    initiated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Error Information
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    call = relationship("Call", back_populates="attempts")

    def __repr__(self) -> str:
        return f"<CallAttempt(id={self.id}, call_id={self.call_id}, attempt={self.attempt_number}, status={self.status})>"

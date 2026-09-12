"""
Absence Report model.
"""
from datetime import datetime, date
from typing import Optional
from uuid import uuid4
from sqlalchemy import String, Date, DateTime, ForeignKey, Enum as SQLEnum, Text, Boolean, Float, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.enums import AbsenceCategory


class AbsenceReport(Base):
    """Structured absence report extracted from call transcript."""

    __tablename__ = "absence_reports"
    __table_args__ = (
        Index('ix_absence_reports_confidence_score', 'confidence_score'),
        Index('ix_absence_reports_follow_up_required', 'follow_up_required'),
        Index('ix_absence_reports_reviewed_by', 'reviewed_by'),
    )

    # Primary Key
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Foreign Keys
    call_id: Mapped[str] = mapped_column(String(36), ForeignKey("calls.id"), nullable=False, unique=True)
    student_id: Mapped[str] = mapped_column(String(36), ForeignKey("students.id"), nullable=False)
    attendance_id: Mapped[str] = mapped_column(String(36), ForeignKey("attendance.id"), nullable=False)

    # Absence Information
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[AbsenceCategory] = mapped_column(
        SQLEnum(AbsenceCategory),
        default=AbsenceCategory.UNKNOWN,
        nullable=False
    )
    duration: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # e.g., "1 day", "2-3 days"
    expected_return_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Validation
    parent_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    follow_up_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)  # 0.0 to 1.0

    # Transcript & Raw Data
    transcript: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_extraction: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Full LLM response

    # Review
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    call = relationship("Call", back_populates="absence_report")
    student = relationship("Student", back_populates="absence_reports")
    attendance = relationship("Attendance", back_populates="absence_reports")
    reviewed_by_user = relationship("User", back_populates="reviewed_reports")
    followups = relationship("FollowUp", back_populates="absence_report")

    def __repr__(self) -> str:
        return f"<AbsenceReport(id={self.id}, category={self.category}, confidence={self.confidence_score})>"

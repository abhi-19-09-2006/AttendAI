"""
Attendance model.
"""
from datetime import datetime, date
from typing import Optional
from uuid import uuid4
from sqlalchemy import String, Date, DateTime, ForeignKey, Enum as SQLEnum, Text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.enums import AttendanceStatus


class Attendance(Base):
    """Attendance record model."""

    __tablename__ = "attendance"
    __table_args__ = (
        UniqueConstraint('student_id', 'date', 'period', name='uq_student_date_period'),
        Index('ix_attendance_date', 'date'),
        Index('ix_attendance_status', 'status'),
        Index('ix_attendance_student_date', 'student_id', 'date'),
    )

    # Primary Key
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Foreign Keys
    student_id: Mapped[str] = mapped_column(String(36), ForeignKey("students.id"), nullable=False)
    recorded_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)

    # Attendance Details
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[AttendanceStatus] = mapped_column(SQLEnum(AttendanceStatus), nullable=False)
    period: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # e.g., "1", "2", or null for all-day
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    student = relationship("Student", back_populates="attendance_records")
    recorded_by_user = relationship("User", back_populates="attendance_records")
    calls = relationship("Call", back_populates="attendance")
    absence_reports = relationship("AbsenceReport", back_populates="attendance")

    def __repr__(self) -> str:
        return f"<Attendance(id={self.id}, student_id={self.student_id}, date={self.date}, status={self.status})>"

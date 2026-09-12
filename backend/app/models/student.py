"""
Student model.
"""
from datetime import datetime, date
from typing import Optional
from uuid import uuid4
from sqlalchemy import String, Date, Integer, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Student(Base):
    """Student model."""

    __tablename__ = "students"

    # Primary Key
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Identification
    student_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)

    # Personal Information
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)

    # Academic Information
    grade_level: Mapped[int] = mapped_column(Integer, nullable=False)
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    parents = relationship("Parent", back_populates="student", cascade="all, delete-orphan")
    attendance_records = relationship("Attendance", back_populates="student", cascade="all, delete-orphan")
    calls = relationship("Call", back_populates="student")
    absence_reports = relationship("AbsenceReport", back_populates="student")
    followups = relationship("FollowUp", back_populates="student")

    def __repr__(self) -> str:
        return f"<Student(id={self.id}, student_id={self.student_id}, name={self.first_name} {self.last_name})>"

    @property
    def full_name(self) -> str:
        """Get student's full name."""
        return f"{self.first_name} {self.last_name}"

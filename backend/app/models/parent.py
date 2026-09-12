"""
Parent/Guardian model.
"""
from datetime import datetime
from typing import Optional
from uuid import uuid4
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship as sa_relationship
from app.core.database import Base
from app.models.enums import ParentRelationship, ContactMethod


class Parent(Base):
    """Parent/Guardian model."""

    __tablename__ = "parents"

    # Primary Key
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Foreign Keys
    student_id: Mapped[str] = mapped_column(String(36), ForeignKey("students.id"), nullable=False, index=True)

    # Relationship to Student
    relationship: Mapped[ParentRelationship] = mapped_column(
        SQLEnum(ParentRelationship),
        nullable=False
    )

    # Personal Information
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Contact Information
    primary_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    secondary_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Preferences
    preferred_contact_method: Mapped[ContactMethod] = mapped_column(
        SQLEnum(ContactMethod),
        default=ContactMethod.PHONE,
        nullable=False
    )
    preferred_language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    is_primary_contact: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    student = sa_relationship("Student", back_populates="parents")
    calls = sa_relationship("Call", back_populates="parent")

    def __repr__(self) -> str:
        return f"<Parent(id={self.id}, name={self.first_name} {self.last_name}, relationship={self.relationship})>"

    @property
    def full_name(self) -> str:
        """Get parent's full name."""
        return f"{self.first_name} {self.last_name}"

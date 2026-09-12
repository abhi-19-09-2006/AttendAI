"""
Call Campaign model.
"""
from datetime import datetime
from typing import Optional
from uuid import uuid4
from sqlalchemy import String, DateTime, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.enums import CampaignStatus


class CallCampaign(Base):
    """Call campaign model for organizing calls."""

    __tablename__ = "call_campaigns"

    # Primary Key
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Campaign Details
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[CampaignStatus] = mapped_column(
        SQLEnum(CampaignStatus),
        default=CampaignStatus.DRAFT,
        nullable=False
    )

    # Foreign Keys
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)

    # Scheduling
    scheduled_start: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    created_by_user = relationship("User", back_populates="created_campaigns")
    calls = relationship("Call", back_populates="campaign")

    def __repr__(self) -> str:
        return f"<CallCampaign(id={self.id}, name={self.name}, status={self.status})>"

"""
Job tracking model for RQ background jobs.

Design rationale:
- Separate Job model (not on Call) keeps transient RQ state separate from business logic
- Database-backed for durability and idempotency
- Links to Call/Campaign for correlation
- Tracks job lifecycle independent of task execution
- Enables audit logging and job history
"""
from datetime import datetime
from typing import Optional
from uuid import uuid4
from sqlalchemy import String, DateTime, ForeignKey, Enum as SQLEnum, Text, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from enum import Enum


class JobStatus(str, Enum):
    """Job status in RQ queue and execution."""
    QUEUED = "queued"
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    DEFERRED = "deferred"  # Scheduled for later


class JobType(str, Enum):
    """Type of background job."""
    SCHEDULE_CAMPAIGN_CALLS = "schedule_campaign_calls"
    INITIATE_CALL = "initiate_call"
    RETRY_CALL = "retry_call"
    CREATE_FOLLOWUP_CALLS = "create_followup_calls"
    GENERATE_REPORT = "generate_report"
    PROCESS_COMPLETION = "process_completion"  # Webhook callback


class Job(Base):
    """Tracks background job execution for idempotency and audit."""

    __tablename__ = "jobs"
    __table_args__ = (
        Index('ix_jobs_rq_id', 'rq_job_id'),
        Index('ix_jobs_type', 'job_type'),
        Index('ix_jobs_status', 'status'),
        Index('ix_jobs_call_id', 'call_id'),
        Index('ix_jobs_campaign_id', 'campaign_id'),
        Index('ix_jobs_created_at', 'created_at'),
    )

    # Primary Key
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # RQ Integration
    # Sized for the prefixed RQ job ids the worker generates
    # (e.g. "followups_<uuid>"), which exceed a bare 36-char UUID.
    rq_job_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        index=True
    )

    # Job Details
    job_type: Mapped[JobType] = mapped_column(SQLEnum(JobType), nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        SQLEnum(JobStatus),
        default=JobStatus.QUEUED,
        nullable=False
    )

    # Correlation
    call_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("calls.id"), nullable=True)
    campaign_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("call_campaigns.id"),
        nullable=True
    )

    # Job Payload & Results
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Input data
    result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Output data
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Retry Information
    retry_count: Mapped[int] = mapped_column(default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(default=3, nullable=False)
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Execution Tracking
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(nullable=True)

    # Idempotency
    idempotency_key: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        index=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    call = relationship("Call", foreign_keys=[call_id])
    campaign = relationship("CallCampaign", foreign_keys=[campaign_id])

    def __repr__(self) -> str:
        return (
            f"<Job(id={self.id}, type={self.job_type}, "
            f"status={self.status}, rq_job_id={self.rq_job_id})>"
        )

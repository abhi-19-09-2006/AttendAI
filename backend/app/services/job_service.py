"""
Job service for managing background job lifecycle and idempotency.
"""
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.logging import get_logger
from app.models.job import Job, JobStatus, JobType
from app.core.rq_config import (
    get_call_queue,
    get_retry_queue,
    get_campaign_queue,
    get_followup_queue
)

logger = get_logger("job_service")

# Statuses that mean a job is still in flight and must not be scheduled again
ACTIVE_JOB_STATUSES = (JobStatus.QUEUED, JobStatus.STARTED, JobStatus.DEFERRED)


class JobService:
    """Service for managing background job lifecycle."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_job(
        self,
        job_type: JobType,
        call_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
        max_retries: int = 3
    ) -> Optional[Job]:
        """
        Create a new job record in database.

        Uses idempotency_key to prevent duplicate jobs.
        Returns existing job if idempotency_key matches.
        """
        # Check for existing job with same idempotency key
        if idempotency_key:
            result = await self.db.execute(
                select(Job).where(Job.idempotency_key == idempotency_key)
            )
            existing = result.scalar_one_or_none()
            if existing:
                logger.info(f"Job already exists with idempotency_key: {idempotency_key}")
                return existing

        job = Job(
            job_type=job_type,
            call_id=call_id,
            campaign_id=campaign_id,
            status=JobStatus.QUEUED,
            payload=payload or {},
            idempotency_key=idempotency_key,
            max_retries=max_retries
        )

        self.db.add(job)
        await self.db.flush()
        await self.db.refresh(job)

        logger.info(
            f"Created job {job.id} type={job_type} "
            f"call_id={call_id} campaign_id={campaign_id}"
        )
        return job

    async def link_rq_job(self, db_job_id: str, rq_job_id: str) -> bool:
        """Link database job to RQ job ID after enqueueing."""
        job = await self.db.get(Job, db_job_id)
        if not job:
            logger.error(f"Job {db_job_id} not found")
            return False

        job.rq_job_id = rq_job_id
        job.status = JobStatus.QUEUED
        await self.db.commit()

        logger.info(f"Linked job {db_job_id} to RQ job {rq_job_id}")
        return True

    async def mark_started(self, db_job_id: str) -> bool:
        """Mark job as started."""
        job = await self.db.get(Job, db_job_id)
        if not job:
            return False

        job.status = JobStatus.STARTED
        job.started_at = datetime.utcnow()
        await self.db.commit()
        return True

    async def mark_completed(self, db_job_id: str, result: Optional[Dict] = None) -> bool:
        """Mark job as completed."""
        job = await self.db.get(Job, db_job_id)
        if not job:
            return False

        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.utcnow()
        job.result = result or {}

        if job.started_at:
            duration = (job.completed_at - job.started_at).total_seconds()
            job.duration_seconds = duration

        await self.db.commit()
        logger.info(f"Job {db_job_id} completed in {job.duration_seconds}s")
        return True

    async def mark_failed(self, db_job_id: str, error_message: str) -> bool:
        """Mark job as failed."""
        job = await self.db.get(Job, db_job_id)
        if not job:
            return False

        job.status = JobStatus.FAILED
        job.completed_at = datetime.utcnow()
        job.error_message = error_message

        if job.started_at:
            duration = (job.completed_at - job.started_at).total_seconds()
            job.duration_seconds = duration

        await self.db.commit()
        logger.error(f"Job {db_job_id} failed: {error_message}")
        return True

    async def schedule_retry(
        self,
        db_job_id: str,
        delay_seconds: int = 300
    ) -> Optional[Job]:
        """
        Schedule a retry of a job.

        Creates a new job with incremented retry_count.
        """
        original_job = await self.db.get(Job, db_job_id)
        if not original_job:
            return None

        if original_job.retry_count >= original_job.max_retries:
            logger.warning(f"Job {db_job_id} exceeded max retries")
            original_job.status = JobStatus.FAILED
            original_job.error_message = "Max retries exceeded"
            await self.db.commit()
            return None

        # Create new retry job
        retry_job = Job(
            job_type=original_job.job_type,
            call_id=original_job.call_id,
            campaign_id=original_job.campaign_id,
            status=JobStatus.DEFERRED,
            payload=original_job.payload,
            retry_count=original_job.retry_count + 1,
            max_retries=original_job.max_retries,
            next_retry_at=datetime.utcnow() + timedelta(seconds=delay_seconds),
            idempotency_key=f"{original_job.idempotency_key}_retry_{original_job.retry_count + 1}"
            if original_job.idempotency_key else None
        )

        self.db.add(retry_job)
        await self.db.flush()
        await self.db.refresh(retry_job)

        logger.info(
            f"Scheduled retry of job {db_job_id}: "
            f"new_job={retry_job.id}, "
            f"retry_count={retry_job.retry_count}, "
            f"retry_at={retry_job.next_retry_at}"
        )
        return retry_job

    async def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID."""
        return await self.db.get(Job, job_id)

    async def get_by_rq_job_id(self, rq_job_id: str) -> Optional[Job]:
        """Get job by RQ job ID."""
        result = await self.db.execute(
            select(Job).where(Job.rq_job_id == rq_job_id)
        )
        return result.scalar_one_or_none()

    async def get_by_idempotency_key(self, idempotency_key: str) -> Optional[Job]:
        """
        Get job by idempotency key.

        Lets callers distinguish "already scheduled" from "newly created",
        which create_job() cannot express (it returns the existing job).
        """
        result = await self.db.execute(
            select(Job).where(Job.idempotency_key == idempotency_key)
        )
        return result.scalar_one_or_none()

    async def get_active_job(
        self,
        job_type: JobType,
        call_id: Optional[str] = None,
        campaign_id: Optional[str] = None
    ) -> Optional[Job]:
        """
        Get an in-flight job (QUEUED/STARTED/DEFERRED) of the given type.

        Used to prevent duplicate scheduling while a job is still pending.
        """
        query = select(Job).where(
            Job.job_type == job_type,
            Job.status.in_(ACTIVE_JOB_STATUSES)
        )
        if call_id is not None:
            query = query.where(Job.call_id == call_id)
        if campaign_id is not None:
            query = query.where(Job.campaign_id == campaign_id)

        result = await self.db.execute(query.order_by(Job.created_at).limit(1))
        return result.scalars().first()

    async def get_due_jobs(
        self,
        job_type: JobType,
        now: datetime,
        limit: int = 100
    ) -> list[Job]:
        """
        Get DEFERRED jobs whose next_retry_at has come due.

        Scheduling state lives in the database, so due work is recovered
        after a worker restart instead of being lost with the process.
        """
        result = await self.db.execute(
            select(Job)
            .where(
                Job.job_type == job_type,
                Job.status == JobStatus.DEFERRED,
                Job.next_retry_at.is_not(None),
                Job.next_retry_at <= now
            )
            .order_by(Job.next_retry_at)
            .limit(limit)
        )
        return list(result.scalars().all())

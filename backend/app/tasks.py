"""
Background job tasks for RQ queue.

These functions are executed by RQ workers (synchronous context).
They use run_async_task() to bridge to async application services.
Reuses existing CallService to avoid duplicating Vapi logic.

Idempotency strategy:
- Each task creates a DB Job record with unique idempotency_key
- Job.idempotency_key is business-level deduplication (not RQ job ID)
- RQ job ID is linked for operational tracking only

Scheduling strategy:
- All scheduling timestamps are naive UTC, matching the naive DateTime columns
- Deferred retries live in the database (Job.next_retry_at), so they are
  recovered by dispatch_due_retries() after a worker restart
- Future-dated campaign/call work uses RQ's own scheduler (enqueue_at)
"""
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone

from app.core.logging import get_logger
from app.core.db_worker import get_worker_session, run_async_task
from app.models import Call, CallStatus, CampaignStatus, Job, JobStatus, JobType

logger = get_logger("tasks")


# Retry eligibility and backoff configuration
RETRY_ELIGIBLE_STATUSES = {CallStatus.NO_ANSWER, CallStatus.BUSY, CallStatus.FAILED}
RETRY_BACKOFF_SECONDS = {
    1: 300,    # First retry: 5 minutes
    2: 900,    # Second retry: 15 minutes
    3: 3600,   # Third retry: 1 hour
}
MAX_RETRIES_DEFAULT = 3
MAX_RETRY_BACKOFF_SECONDS = 3600

# Only ACTIVE campaigns schedule calls; DRAFT/PAUSED/COMPLETED are left alone
CAMPAIGN_SCHEDULABLE_STATUSES = {CampaignStatus.ACTIVE}


def _utcnow() -> datetime:
    """
    Current UTC time as a naive datetime.

    Timestamp columns are naive DateTime, so everything is normalised to
    naive UTC to keep comparisons and backoff arithmetic unambiguous.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _as_naive_utc(value: Optional[datetime]) -> Optional[datetime]:
    """Normalise a possibly timezone-aware datetime to naive UTC."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


@asynccontextmanager
async def _task_session(session=None):
    """
    Yield the caller's session, or open a fresh worker session.

    RQ tasks own their session; callers that already hold one (API code,
    tests) pass it in so the work joins their transaction.
    """
    if session is not None:
        yield session
    else:
        async with get_worker_session() as owned_session:
            yield owned_session


async def _initiate_pending_call_async(call_id: str, job_id: str) -> Dict[str, Any]:
    """
    Async implementation: Initiate a pending call via Vapi.
    Reuses CallService.initiate_call() to avoid duplicating logic.
    """
    from app.services.call_service import CallService
    from app.services.vapi_provider import VapiProvider
    from app.services.job_service import JobService

    async with get_worker_session() as session:
        try:
            # Get call and verify it's still pending
            call = await session.get(Call, call_id)
            if not call:
                logger.error(f"Call {call_id} not found")
                return {"status": "failed", "reason": "call_not_found"}

            if call.status not in [CallStatus.PENDING, CallStatus.QUEUED]:
                logger.warning(f"Call {call_id} is in {call.status} status, skipping")
                return {"status": "skipped", "reason": f"status_{call.status.value}"}

            # Mark job as started
            job_service = JobService(session)
            await job_service.mark_started(job_id)

            # Initiate call using existing service
            call_service = CallService(session, VapiProvider())
            success = await call_service.initiate_call(call_id)

            if success:
                await job_service.mark_completed(
                    job_id,
                    {"vapi_call_id": call.vapi_call_id}
                )
                logger.info(f"Call {call_id} initiated via Vapi: {call.vapi_call_id}")
                return {"status": "completed", "vapi_call_id": call.vapi_call_id}
            else:
                await job_service.mark_failed(job_id, "Failed to initiate call")
                return {"status": "failed", "reason": "initiate_failed"}

        except Exception as e:
            logger.error(f"Error initiating call {call_id}: {str(e)}", exc_info=True)
            async with get_worker_session() as session2:
                job_service = JobService(session2)
                await job_service.mark_failed(job_id, str(e))
            return {"status": "error", "error": str(e)}


def initiate_pending_call(call_id: str, job_id: str) -> Dict[str, Any]:
    """
    RQ task: Initiate a pending call.
    Synchronous entry point that bridges to async implementation.
    """
    return run_async_task(_initiate_pending_call_async(call_id, job_id))


async def _retry_failed_call_async(
    call_id: str,
    job_id: str,
    retry_count: int,
    session=None
) -> Dict[str, Any]:
    """
    Async implementation: Retry a failed call.
    Eligible statuses: NO_ANSWER, BUSY, transient FAILED
    """
    from app.services.call_service import CallService
    from app.services.vapi_provider import VapiProvider
    from app.services.job_service import JobService

    async with _task_session(session) as s:
        try:
            call = await s.get(Call, call_id)
            if not call:
                logger.error(f"Call {call_id} not found for retry")
                return {"status": "failed", "reason": "call_not_found"}

            # Check if call status is retryable
            if call.status not in RETRY_ELIGIBLE_STATUSES:
                logger.warning(
                    f"Call {call_id} status {call.status} is not retryable"
                )
                return {"status": "skipped", "reason": f"not_retryable_{call.status.value}"}

            # Check if max retries exceeded
            if retry_count >= call.max_retries:
                call.status = CallStatus.UNREACHABLE
                await s.commit()
                logger.info(f"Call {call_id} marked UNREACHABLE after {retry_count} retries")
                return {"status": "completed", "reason": "max_retries_reached"}

            # Reset call to PENDING for re-initiation
            call.status = CallStatus.PENDING
            call.retry_count = retry_count
            await s.commit()

            # Mark job as started
            job_service = JobService(s)
            await job_service.mark_started(job_id)

            # Initiate retry
            call_service = CallService(s, VapiProvider())
            success = await call_service.initiate_call(call_id)

            if success:
                await job_service.mark_completed(
                    job_id,
                    {"retry_count": retry_count, "vapi_call_id": call.vapi_call_id}
                )
                logger.info(f"Retry {retry_count} initiated for call {call_id}")
                return {
                    "status": "completed",
                    "retry_count": retry_count,
                    "vapi_call_id": call.vapi_call_id
                }
            else:
                await job_service.mark_failed(job_id, "Retry initiation failed")
                return {"status": "failed", "reason": "retry_initiation_failed"}

        except Exception as e:
            logger.error(f"Error retrying call {call_id}: {str(e)}", exc_info=True)
            async with get_worker_session() as session2:
                await JobService(session2).mark_failed(job_id, str(e))
            return {"status": "error", "error": str(e)}


def retry_failed_call(call_id: str, job_id: str, retry_count: int) -> Dict[str, Any]:
    """
    RQ task: Retry a failed call.
    Synchronous entry point that bridges to async implementation.
    """
    return run_async_task(_retry_failed_call_async(call_id, job_id, retry_count))


async def _activate_campaign_async(campaign_id: str, session=None) -> Dict[str, Any]:
    """
    Async implementation: Activate a campaign by queueing its scheduling job.

    One activation per campaign: the activation idempotency key plus the
    in-flight job check mean repeated activation requests are no-ops.
    Honours campaign.scheduled_start by deferring to RQ's scheduler.
    """
    from app.models import CallCampaign
    from app.core.rq_config import get_campaign_queue
    from app.services.job_service import JobService

    async with _task_session(session) as s:
        campaign = await s.get(CallCampaign, campaign_id)
        if not campaign:
            logger.error(f"Campaign {campaign_id} not found")
            return {"status": "failed", "reason": "campaign_not_found"}

        if campaign.status not in CAMPAIGN_SCHEDULABLE_STATUSES:
            logger.info(f"Campaign {campaign_id} is {campaign.status}, not activating")
            return {
                "status": "skipped",
                "reason": f"campaign_not_active_{campaign.status.value}"
            }

        job_service = JobService(s)
        idempotency_key = f"campaign_activation_{campaign_id}"

        existing = await job_service.get_by_idempotency_key(idempotency_key)
        if existing:
            logger.info(f"Campaign {campaign_id} already activated (job {existing.id})")
            return {
                "status": "skipped",
                "reason": "already_activated",
                "job_id": existing.id
            }

        pending = await job_service.get_active_job(
            JobType.SCHEDULE_CAMPAIGN_CALLS, campaign_id=campaign_id
        )
        if pending:
            logger.info(f"Campaign {campaign_id} already has pending job {pending.id}")
            return {
                "status": "skipped",
                "reason": "already_scheduled",
                "job_id": pending.id
            }

        scheduled_start = _as_naive_utc(campaign.scheduled_start)
        now = _utcnow()
        deferred = bool(scheduled_start and scheduled_start > now)

        job = await job_service.create_job(
            job_type=JobType.SCHEDULE_CAMPAIGN_CALLS,
            campaign_id=campaign_id,
            payload={
                "scheduled_start": scheduled_start.isoformat() if scheduled_start else None
            },
            idempotency_key=idempotency_key
        )

        queue = get_campaign_queue()
        rq_job_id = f"campaign_{campaign_id}"
        if deferred:
            rq_job = queue.enqueue_at(
                scheduled_start.replace(tzinfo=timezone.utc),
                schedule_campaign_calls,
                campaign_id,
                job.id,
                job_id=rq_job_id
            )
        else:
            rq_job = queue.enqueue(
                schedule_campaign_calls,
                campaign_id,
                job.id,
                job_id=rq_job_id
            )

        await job_service.link_rq_job(job.id, rq_job.id)
        if deferred:
            job.status = JobStatus.DEFERRED
            await s.commit()

        logger.info(
            f"Activated campaign {campaign_id} (job {job.id}, "
            f"{'deferred to ' + str(scheduled_start) if deferred else 'immediate'})"
        )

        return {
            "status": "deferred" if deferred else "scheduled",
            "campaign_id": campaign_id,
            "job_id": job.id,
            "scheduled_start": scheduled_start.isoformat() if scheduled_start else None
        }


def activate_campaign(campaign_id: str) -> Dict[str, Any]:
    """
    RQ task: Activate a campaign, queueing exactly one scheduling job.
    Synchronous entry point that bridges to async implementation.
    """
    return run_async_task(_activate_campaign_async(campaign_id))


async def _schedule_campaign_calls_async(
    campaign_id: str,
    job_id: str,
    session=None
) -> Dict[str, Any]:
    """
    Async implementation: Schedule all calls for a campaign.

    Enqueues one initiation job per PENDING call. Calls carrying a future
    scheduled_time go to RQ's scheduler instead of the ready queue, and the
    per-call idempotency key stops a re-run from enqueueing a second job.
    """
    from sqlalchemy import select, and_
    from app.models import CallCampaign
    from app.core.rq_config import get_call_queue
    from app.services.job_service import JobService

    async with _task_session(session) as s:
        job_service = JobService(s)
        try:
            campaign = await s.get(CallCampaign, campaign_id)
            if not campaign:
                logger.error(f"Campaign {campaign_id} not found")
                await job_service.mark_failed(job_id, "Campaign not found")
                return {"status": "failed", "reason": "campaign_not_found"}

            if campaign.status not in CAMPAIGN_SCHEDULABLE_STATUSES:
                reason = f"campaign_not_active_{campaign.status.value}"
                logger.info(f"Campaign {campaign_id} is {campaign.status}, skipping")
                await job_service.mark_completed(
                    job_id, {"skipped": True, "reason": reason}
                )
                return {"status": "skipped", "reason": reason}

            now = _utcnow()
            scheduled_start = _as_naive_utc(campaign.scheduled_start)
            if scheduled_start and scheduled_start > now:
                logger.info(
                    f"Campaign {campaign_id} starts at {scheduled_start}, not due yet"
                )
                return {
                    "status": "deferred",
                    "reason": "scheduled_start_in_future",
                    "scheduled_start": scheduled_start.isoformat()
                }

            await job_service.mark_started(job_id)

            # Find all PENDING calls for this campaign
            query = select(Call).where(
                and_(
                    Call.campaign_id == campaign_id,
                    Call.status == CallStatus.PENDING
                )
            )
            result = await s.execute(query)
            pending_calls = result.scalars().all()

            logger.info(f"Scheduling {len(pending_calls)} calls for campaign {campaign_id}")

            queue = get_call_queue()
            job_ids = []
            deferred_ids = []
            skipped = 0

            for call in pending_calls:
                # Idempotency key: campaign_call_{campaign_id}_{call_id}
                # Prevents duplicate jobs if campaign activated twice
                idempotency_key = f"campaign_call_{campaign_id}_{call.id}"

                if await job_service.get_by_idempotency_key(idempotency_key):
                    skipped += 1
                    continue

                db_job = await job_service.create_job(
                    job_type=JobType.INITIATE_CALL,
                    call_id=call.id,
                    campaign_id=campaign_id,
                    idempotency_key=idempotency_key
                )

                call_time = _as_naive_utc(call.scheduled_time)
                is_deferred = bool(call_time and call_time > now)

                try:
                    if is_deferred:
                        rq_job = queue.enqueue_at(
                            call_time.replace(tzinfo=timezone.utc),
                            initiate_pending_call,
                            call.id,
                            db_job.id,
                            job_id=f"call_{call.id}"
                        )
                    else:
                        rq_job = queue.enqueue(
                            initiate_pending_call,
                            call.id,
                            db_job.id,
                            job_id=f"call_{call.id}"
                        )
                except Exception as e:
                    logger.error(f"Failed to enqueue call {call.id}: {str(e)}")
                    continue

                await job_service.link_rq_job(db_job.id, rq_job.id)
                if is_deferred:
                    db_job.status = JobStatus.DEFERRED
                    await s.commit()
                    deferred_ids.append(rq_job.id)
                else:
                    job_ids.append(rq_job.id)

            await job_service.mark_completed(
                job_id,
                {
                    "calls_enqueued": len(job_ids),
                    "calls_deferred": len(deferred_ids),
                    "calls_skipped": skipped,
                    "rq_job_ids": job_ids + deferred_ids
                }
            )

            return {
                "status": "completed",
                "calls_enqueued": len(job_ids),
                "calls_deferred": len(deferred_ids),
                "calls_skipped": skipped,
                "campaign_id": campaign_id
            }

        except Exception as e:
            logger.error(f"Error scheduling campaign {campaign_id}: {str(e)}", exc_info=True)
            async with get_worker_session() as session2:
                await JobService(session2).mark_failed(job_id, str(e))
            return {"status": "error", "error": str(e)}


def schedule_campaign_calls(campaign_id: str, job_id: str) -> Dict[str, Any]:
    """
    RQ task: Schedule all calls for a campaign.
    Synchronous entry point that bridges to async implementation.
    """
    return run_async_task(_schedule_campaign_calls_async(campaign_id, job_id))


async def _create_followup_calls_async(job_id: str, session=None) -> Dict[str, Any]:
    """
    Async implementation: Create follow-up tasks for calls that need them.

    Creates follow-ups only where one is actually required and not already
    present:
    - Calls with CALLBACK_REQUESTED status
    - Unreviewed absence reports that are low confidence or flagged

    Type/priority follow CallService._create_followup so both paths classify
    follow-ups the same way.
    """
    from sqlalchemy import select, and_
    from datetime import timedelta
    from app.models import AbsenceReport, FollowUp, Call, AbsenceCategory
    from app.models.enums import FollowUpType, FollowUpPriority, FollowUpStatus
    from app.services.job_service import JobService

    async with _task_session(session) as s:
        job_service = JobService(s)
        try:
            await job_service.mark_started(job_id)

            due_date = _utcnow().date() + timedelta(days=1)

            # 1. Calls with CALLBACK_REQUESTED status
            callback_query = select(Call).where(Call.status == CallStatus.CALLBACK_REQUESTED)
            callback_result = await s.execute(callback_query)
            callback_calls = callback_result.scalars().all()

            # 2. Absence reports with low confidence or flagged for follow-up
            followup_query = select(AbsenceReport).where(
                and_(
                    (AbsenceReport.confidence_score < 0.85)
                    | (AbsenceReport.follow_up_required == True),
                    AbsenceReport.reviewed_by.is_(None)
                )
            )
            followup_result = await s.execute(followup_query)
            low_confidence_reports = followup_result.scalars().all()

            created_followups = []

            for call in callback_calls:
                # Dedupe on (call, type): a report follow-up also carries
                # call_id and must not suppress the callback follow-up.
                existing = await s.execute(
                    select(FollowUp).where(
                        and_(
                            FollowUp.call_id == call.id,
                            FollowUp.type == FollowUpType.CALLBACK_REQUESTED
                        )
                    )
                )
                if existing.scalars().first():
                    continue

                followup = FollowUp(
                    call_id=call.id,
                    student_id=call.student_id,
                    type=FollowUpType.CALLBACK_REQUESTED,
                    priority=FollowUpPriority.HIGH,
                    status=FollowUpStatus.PENDING,
                    due_date=due_date,
                    description="Parent requested callback for student"
                )
                s.add(followup)
                created_followups.append(followup)

            for report in low_confidence_reports:
                existing = await s.execute(
                    select(FollowUp).where(FollowUp.absence_report_id == report.id)
                )
                if existing.scalars().first():
                    continue

                # Same classification as CallService._create_followup
                followup_type = FollowUpType.LOW_CONFIDENCE
                priority = FollowUpPriority.MEDIUM
                description = (
                    f"Review absence report - confidence: {report.confidence_score:.2f}"
                )

                if report.confidence_score < 0.5:
                    priority = FollowUpPriority.HIGH
                    description = (
                        f"Low confidence extraction ({report.confidence_score:.2f}) "
                        "- verify information"
                    )
                elif report.category == AbsenceCategory.MEDICAL:
                    followup_type = FollowUpType.MEDICAL_VERIFICATION
                    description = (
                        "Medical absence - verify and collect documentation if needed"
                    )

                followup = FollowUp(
                    absence_report_id=report.id,
                    call_id=report.call_id,
                    student_id=report.student_id,
                    type=followup_type,
                    priority=priority,
                    status=FollowUpStatus.PENDING,
                    due_date=due_date,
                    description=description
                )
                s.add(followup)
                created_followups.append(followup)

            await s.commit()

            await job_service.mark_completed(
                job_id,
                {
                    "followups_created": len(created_followups),
                    "callback_calls": len(callback_calls),
                    "low_confidence_reports": len(low_confidence_reports)
                }
            )

            logger.info(
                f"Created {len(created_followups)} follow-up tasks "
                f"(callbacks: {len(callback_calls)}, low_conf: {len(low_confidence_reports)})"
            )

            return {
                "status": "completed",
                "followups_created": len(created_followups)
            }

        except Exception as e:
            logger.error(f"Error creating follow-ups: {str(e)}", exc_info=True)
            async with get_worker_session() as session2:
                await JobService(session2).mark_failed(job_id, str(e))
            return {"status": "error", "error": str(e)}


def create_followup_calls(job_id: str) -> Dict[str, Any]:
    """
    RQ task: Create follow-up tasks for calls that need them.
    Synchronous entry point that bridges to async implementation.
    """
    return run_async_task(_create_followup_calls_async(job_id))


async def _schedule_followups_async(session=None) -> Dict[str, Any]:
    """
    Async implementation: Queue a follow-up creation batch.

    Only one batch may be in flight at a time, so repeated scheduling does
    not produce duplicate follow-up jobs (and therefore no duplicate
    follow-ups from concurrent batches).
    """
    from app.core.rq_config import get_followup_queue
    from app.services.job_service import JobService

    async with _task_session(session) as s:
        job_service = JobService(s)

        pending = await job_service.get_active_job(JobType.CREATE_FOLLOWUP_CALLS)
        if pending:
            logger.info(f"Follow-up batch already pending (job {pending.id})")
            return {
                "status": "skipped",
                "reason": "batch_already_pending",
                "job_id": pending.id
            }

        job = await job_service.create_job(job_type=JobType.CREATE_FOLLOWUP_CALLS)

        queue = get_followup_queue()
        rq_job = queue.enqueue(create_followup_calls, job.id, job_id=f"followups_{job.id}")
        await job_service.link_rq_job(job.id, rq_job.id)

        logger.info(f"Queued follow-up batch job {job.id}")
        return {"status": "scheduled", "job_id": job.id, "rq_job_id": rq_job.id}


def schedule_followups() -> Dict[str, Any]:
    """
    RQ task: Queue a follow-up creation batch if none is in flight.
    Synchronous entry point that bridges to async implementation.
    """
    return run_async_task(_schedule_followups_async())


async def _schedule_retry_async(
    call_id: str,
    retry_number: int,
    session=None
) -> Dict[str, Any]:
    """
    Async implementation: Schedule a retry for a failed call.

    Creates a DEFERRED Job carrying next_retry_at. dispatch_due_retries()
    later enqueues the actual retry, so a scheduled retry survives a worker
    restart. Scheduling is idempotent per (call, attempt) and never creates a
    second retry while one is still in flight.
    """
    from app.services.job_service import JobService

    async with _task_session(session) as s:
        try:
            call = await s.get(Call, call_id)
            if not call:
                logger.error(f"Call {call_id} not found for retry scheduling")
                return {"status": "failed", "reason": "call_not_found"}

            if call.status not in RETRY_ELIGIBLE_STATUSES:
                logger.warning(f"Call {call_id} status {call.status} not retryable")
                return {"status": "skipped", "reason": "not_retryable"}

            max_retries = (
                call.max_retries if call.max_retries is not None else MAX_RETRIES_DEFAULT
            )
            if retry_number > max_retries:
                logger.warning(f"Call {call_id} exceeded max retries ({max_retries})")
                call.status = CallStatus.UNREACHABLE
                await s.commit()
                return {"status": "skipped", "reason": "max_retries_exceeded"}

            job_service = JobService(s)
            idempotency_key = f"retry_call_{call_id}_attempt_{retry_number}"

            # Same attempt already scheduled: return it untouched so the
            # originally computed next_retry_at is never pushed forward.
            existing = await job_service.get_by_idempotency_key(idempotency_key)
            if existing:
                logger.info(f"Retry job already exists: {idempotency_key}")
                return {
                    "status": "skipped",
                    "reason": "already_scheduled",
                    "job_id": existing.id,
                    "next_retry_at": (
                        existing.next_retry_at.isoformat()
                        if existing.next_retry_at else None
                    ),
                }

            # A retry for a different attempt is still in flight
            pending = await job_service.get_active_job(
                JobType.RETRY_CALL, call_id=call_id
            )
            if pending:
                logger.info(f"Call {call_id} already has pending retry job {pending.id}")
                return {
                    "status": "skipped",
                    "reason": "retry_already_pending",
                    "job_id": pending.id,
                }

            # Deterministic backoff for this attempt number
            delay_seconds = RETRY_BACKOFF_SECONDS.get(
                retry_number, MAX_RETRY_BACKOFF_SECONDS
            )
            retry_at = _utcnow() + timedelta(seconds=delay_seconds)

            retry_job = await job_service.create_job(
                job_type=JobType.RETRY_CALL,
                call_id=call_id,
                campaign_id=call.campaign_id,
                payload={"retry_number": retry_number},
                idempotency_key=idempotency_key,
                max_retries=max_retries
            )

            retry_job.status = JobStatus.DEFERRED
            retry_job.next_retry_at = retry_at
            retry_job.retry_count = retry_number
            await s.commit()

            logger.info(
                f"Scheduled retry {retry_number} for call {call_id} "
                f"at {retry_at} (delay: {delay_seconds}s)"
            )

            return {
                "status": "scheduled",
                "retry_number": retry_number,
                "next_retry_at": retry_at.isoformat(),
                "job_id": retry_job.id
            }

        except Exception as e:
            logger.error(f"Error scheduling retry for call {call_id}: {str(e)}", exc_info=True)
            return {"status": "error", "error": str(e)}


def schedule_retry(call_id: str, retry_number: int = 1) -> Dict[str, Any]:
    """
    RQ task: Schedule a retry for a failed call.
    Creates a Job with DEFERRED status and next_retry_at timestamp.
    Synchronous entry point that bridges to async implementation.
    """
    return run_async_task(_schedule_retry_async(call_id, retry_number))


async def _dispatch_due_retries_async(limit: int = 100, session=None) -> Dict[str, Any]:
    """
    Async implementation: Enqueue retry jobs that have come due.

    Reads DEFERRED retry jobs from the database rather than in-process
    state, so retries scheduled before a restart are still dispatched.
    Jobs whose call is no longer retryable are closed out instead of run.
    """
    from app.core.rq_config import get_retry_queue
    from app.services.job_service import JobService

    async with _task_session(session) as s:
        job_service = JobService(s)
        now = _utcnow()
        due_jobs = await job_service.get_due_jobs(JobType.RETRY_CALL, now, limit=limit)

        dispatched = []
        cancelled = []
        queue = None

        for job in due_jobs:
            call = await s.get(Call, job.call_id) if job.call_id else None

            if not call or call.status not in RETRY_ELIGIBLE_STATUSES:
                reason = "call_not_found" if not call else f"not_retryable_{call.status.value}"
                await job_service.mark_completed(job.id, {"skipped": True, "reason": reason})
                cancelled.append(job.id)
                continue

            retry_number = job.retry_count or 1
            try:
                if queue is None:
                    queue = get_retry_queue()
                rq_job = queue.enqueue(
                    retry_failed_call,
                    call.id,
                    job.id,
                    retry_number,
                    job_id=f"retry_{call.id}_{retry_number}"
                )
            except Exception as e:
                # Leave the job DEFERRED so the next dispatch picks it up again
                logger.error(f"Failed to enqueue retry job {job.id}: {str(e)}")
                continue

            await job_service.link_rq_job(job.id, rq_job.id)
            dispatched.append(job.id)

        if dispatched or cancelled:
            logger.info(
                f"Retry dispatch: {len(dispatched)} enqueued, {len(cancelled)} cancelled"
            )

        return {
            "status": "completed",
            "dispatched": len(dispatched),
            "cancelled": len(cancelled),
            "job_ids": dispatched
        }


def dispatch_due_retries(limit: int = 100) -> Dict[str, Any]:
    """
    RQ task: Enqueue all retry jobs whose next_retry_at has passed.
    Run periodically; it is the recovery path after a worker restart.
    """
    return run_async_task(_dispatch_due_retries_async(limit))

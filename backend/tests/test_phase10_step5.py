"""
Tests for Phase 10 Step 5: retry, campaign and follow-up scheduling.

Focus on:
- Deterministic, timezone-safe retry backoff that survives worker restart
- Campaign activation/scheduling without duplicate jobs
- Follow-up batches that create only the follow-ups that are required

RQ queues are replaced with an in-memory double, so no Redis round-trip and
no Vapi call happens here.
"""
import pytest
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import tasks
from app.core import rq_config
from app.models import (
    AbsenceReport,
    Attendance,
    Call,
    CallAttempt,
    CallCampaign,
    CallStatus,
    CampaignStatus,
    FollowUp,
    Job,
    JobStatus,
    JobType,
    Parent,
    Student,
    User,
)
from app.models.enums import (
    AbsenceCategory,
    AttendanceStatus,
    ContactMethod,
    FollowUpPriority,
    FollowUpStatus,
    FollowUpType,
    ParentRelationship,
    UserRole,
)
from app.services.job_service import JobService


class FakeQueue:
    """In-memory stand-in for an RQ queue."""

    def __init__(self):
        self.enqueued = []   # (func_name, args, rq_job_id)
        self.scheduled = []  # (func_name, args, rq_job_id, run_at)

    def enqueue(self, func, *args, **kwargs):
        rq_job_id = kwargs.get("job_id") or str(uuid4())
        self.enqueued.append((func.__name__, args, rq_job_id))
        return SimpleNamespace(id=rq_job_id)

    def enqueue_at(self, run_at, func, *args, **kwargs):
        rq_job_id = kwargs.get("job_id") or str(uuid4())
        self.scheduled.append((func.__name__, args, rq_job_id, run_at))
        return SimpleNamespace(id=rq_job_id)


@pytest.fixture
def queue(monkeypatch) -> FakeQueue:
    """Route every queue accessor to a single in-memory queue."""
    fake = FakeQueue()
    for name in (
        "get_queue",
        "get_call_queue",
        "get_retry_queue",
        "get_campaign_queue",
        "get_followup_queue",
    ):
        monkeypatch.setattr(rq_config, name, lambda *a, **kw: fake)
    return fake


@pytest.fixture
async def seed(db_session: AsyncSession):
    """
    Create the FK chain Step 5 needs, then remove everything it touched.

    IDs are unique per test so runs never collide on the shared dev database.
    """
    suffix = uuid4().hex[:12]

    user = User(
        id=f"u-{suffix}",
        email=f"step5-{suffix}@test.com",
        hashed_password="hash",
        full_name="Step5 Teacher",
        role=UserRole.FACULTY,
        is_active=True,
    )
    student = Student(
        id=f"s-{suffix}",
        student_id=f"STU-{suffix}",
        first_name="Step",
        last_name="Five",
        date_of_birth=date(2010, 1, 1),
        grade_level=9,
        is_active=True,
    )
    parent = Parent(
        id=f"p-{suffix}",
        student_id=student.id,
        relationship=ParentRelationship.MOTHER,
        first_name="Pat",
        last_name="Five",
        primary_phone="+15551230000",
        preferred_contact_method=ContactMethod.PHONE,
        preferred_language="en",
        is_primary_contact=True,
    )
    attendance = Attendance(
        id=f"a-{suffix}",
        student_id=student.id,
        recorded_by=user.id,
        date=date(2026, 9, 14),
        status=AttendanceStatus.ABSENT,
    )
    campaign = CallCampaign(
        id=f"c-{suffix}",
        name=f"Step5 Campaign {suffix}",
        status=CampaignStatus.ACTIVE,
        created_by=user.id,
    )

    db_session.add_all([user, student, parent, attendance, campaign])
    await db_session.commit()

    ctx = SimpleNamespace(
        suffix=suffix,
        user=user,
        student=student,
        parent=parent,
        attendance=attendance,
        campaign=campaign,
        call_ids=[],
        report_ids=[],
        extra_job_ids=[],
    )

    async def make_call(status=CallStatus.PENDING, **kwargs):
        fields = {
            "id": f"call-{suffix}-{len(ctx.call_ids)}",
            "campaign_id": campaign.id,
            "student_id": student.id,
            "parent_id": parent.id,
            "attendance_id": attendance.id,
            "status": status,
            "phone_number_called": "+15551230000",
            "retry_count": 0,
            "max_retries": 3,
        }
        fields.update(kwargs)
        call = Call(**fields)
        db_session.add(call)
        await db_session.commit()
        ctx.call_ids.append(call.id)
        return call

    async def make_report(call, **kwargs):
        fields = {
            "id": f"rep-{suffix}-{len(ctx.report_ids)}",
            "call_id": call.id,
            "student_id": student.id,
            "attendance_id": attendance.id,
            "reason": "Unwell",
            "category": AbsenceCategory.OTHER,
            "confidence_score": 0.6,
            "follow_up_required": True,
            "transcript": "",
        }
        fields.update(kwargs)
        report = AbsenceReport(**fields)
        db_session.add(report)
        await db_session.commit()
        ctx.report_ids.append(report.id)
        return report

    ctx.make_call = make_call
    ctx.make_report = make_report

    yield ctx

    # FK-safe teardown of everything this test created
    if ctx.call_ids:
        await db_session.execute(delete(Job).where(Job.call_id.in_(ctx.call_ids)))
    if ctx.extra_job_ids:
        await db_session.execute(delete(Job).where(Job.id.in_(ctx.extra_job_ids)))
    await db_session.execute(delete(Job).where(Job.campaign_id == campaign.id))
    await db_session.execute(delete(FollowUp).where(FollowUp.student_id == student.id))
    await db_session.execute(
        delete(AbsenceReport).where(AbsenceReport.student_id == student.id)
    )
    if ctx.call_ids:
        await db_session.execute(delete(CallAttempt).where(CallAttempt.call_id.in_(ctx.call_ids)))
    await db_session.execute(delete(Call).where(Call.campaign_id == campaign.id))
    await db_session.execute(delete(CallCampaign).where(CallCampaign.id == campaign.id))
    await db_session.execute(delete(Attendance).where(Attendance.id == attendance.id))
    await db_session.execute(delete(Parent).where(Parent.id == parent.id))
    await db_session.execute(delete(Student).where(Student.id == student.id))
    await db_session.execute(delete(User).where(User.id == user.id))
    await db_session.commit()


async def _jobs_for_call(db_session: AsyncSession, call_id: str, job_type: JobType):
    result = await db_session.execute(
        select(Job).where(Job.call_id == call_id, Job.job_type == job_type)
    )
    return list(result.scalars().all())


class TestRetryScheduling:
    """Retry scheduling: deterministic, idempotent, bounded."""

    async def test_schedules_deferred_job_with_backoff(self, db_session, seed):
        call = await seed.make_call(status=CallStatus.NO_ANSWER)

        result = await tasks._schedule_retry_async(call.id, 1, session=db_session)

        assert result["status"] == "scheduled"
        assert result["retry_number"] == 1

        jobs = await _jobs_for_call(db_session, call.id, JobType.RETRY_CALL)
        assert len(jobs) == 1
        job = jobs[0]
        assert job.status == JobStatus.DEFERRED
        assert job.retry_count == 1
        assert job.next_retry_at is not None
        assert job.idempotency_key == f"retry_call_{call.id}_attempt_1"

    async def test_backoff_is_deterministic_per_attempt(self, db_session, seed):
        expected = {1: 300, 2: 900, 3: 3600}

        for attempt, delay in expected.items():
            call = await seed.make_call(status=CallStatus.NO_ANSWER)
            before = datetime.now(timezone.utc).replace(tzinfo=None)

            result = await tasks._schedule_retry_async(call.id, attempt, session=db_session)

            assert result["status"] == "scheduled"
            scheduled_at = datetime.fromisoformat(result["next_retry_at"])
            actual = (scheduled_at - before).total_seconds()
            assert delay <= actual <= delay + 10, f"attempt {attempt}: {actual}s"

    async def test_scheduling_is_idempotent(self, db_session, seed):
        call = await seed.make_call(status=CallStatus.BUSY)

        first = await tasks._schedule_retry_async(call.id, 1, session=db_session)
        second = await tasks._schedule_retry_async(call.id, 1, session=db_session)

        assert first["status"] == "scheduled"
        assert second["status"] == "skipped"
        assert second["reason"] == "already_scheduled"
        # The originally computed time is not pushed forward by a re-schedule
        assert second["next_retry_at"] == first["next_retry_at"]
        assert second["job_id"] == first["job_id"]

        jobs = await _jobs_for_call(db_session, call.id, JobType.RETRY_CALL)
        assert len(jobs) == 1

    async def test_no_second_retry_while_one_is_pending(self, db_session, seed):
        call = await seed.make_call(status=CallStatus.NO_ANSWER)

        first = await tasks._schedule_retry_async(call.id, 1, session=db_session)
        second = await tasks._schedule_retry_async(call.id, 2, session=db_session)

        assert first["status"] == "scheduled"
        assert second["status"] == "skipped"
        assert second["reason"] == "retry_already_pending"

        jobs = await _jobs_for_call(db_session, call.id, JobType.RETRY_CALL)
        assert len(jobs) == 1

    async def test_respects_call_max_retries(self, db_session, seed):
        call = await seed.make_call(status=CallStatus.NO_ANSWER, max_retries=1)

        result = await tasks._schedule_retry_async(call.id, 2, session=db_session)

        assert result["status"] == "skipped"
        assert result["reason"] == "max_retries_exceeded"
        assert not await _jobs_for_call(db_session, call.id, JobType.RETRY_CALL)

        await db_session.refresh(call)
        assert call.status == CallStatus.UNREACHABLE

    async def test_only_eligible_failures_are_retried(self, db_session, seed):
        for status in (CallStatus.COMPLETED, CallStatus.ANSWERED, CallStatus.UNREACHABLE):
            call = await seed.make_call(status=status)

            result = await tasks._schedule_retry_async(call.id, 1, session=db_session)

            assert result["status"] == "skipped", status
            assert result["reason"] == "not_retryable"
            assert not await _jobs_for_call(db_session, call.id, JobType.RETRY_CALL)

    async def test_missing_call_is_not_scheduled(self, db_session, seed):
        result = await tasks._schedule_retry_async("does-not-exist", 1, session=db_session)

        assert result["status"] == "failed"
        assert result["reason"] == "call_not_found"

    async def test_schedule_time_is_naive_utc(self, db_session, seed):
        call = await seed.make_call(status=CallStatus.FAILED)
        before = datetime.now(timezone.utc).replace(tzinfo=None)

        await tasks._schedule_retry_async(call.id, 1, session=db_session)

        job = (await _jobs_for_call(db_session, call.id, JobType.RETRY_CALL))[0]
        assert job.next_retry_at.tzinfo is None
        delta = (job.next_retry_at - before).total_seconds()
        assert 300 <= delta <= 310


class TestRetryDispatch:
    """Due retries are recovered from the database, not from process state."""

    async def _defer(self, db_session, call, retry_number=1, due_in_seconds=-60):
        """Persist a DEFERRED retry job as a pre-restart schedule would."""
        job = await JobService(db_session).create_job(
            job_type=JobType.RETRY_CALL,
            call_id=call.id,
            payload={"retry_number": retry_number},
            idempotency_key=f"retry_call_{call.id}_attempt_{retry_number}",
        )
        job.status = JobStatus.DEFERRED
        job.retry_count = retry_number
        job.next_retry_at = tasks._utcnow() + timedelta(seconds=due_in_seconds)
        await db_session.commit()
        return job

    async def test_due_job_is_enqueued_after_restart(self, db_session, seed, queue):
        call = await seed.make_call(status=CallStatus.NO_ANSWER)
        job = await self._defer(db_session, call)

        result = await tasks._dispatch_due_retries_async(session=db_session)

        assert result["status"] == "completed"
        assert job.id in result["job_ids"]

        await db_session.refresh(job)
        assert job.status == JobStatus.QUEUED
        assert job.rq_job_id == f"retry_{call.id}_1"
        assert ("retry_failed_call", (call.id, job.id, 1), f"retry_{call.id}_1") in queue.enqueued

    async def test_future_job_is_left_deferred(self, db_session, seed, queue):
        call = await seed.make_call(status=CallStatus.NO_ANSWER)
        job = await self._defer(db_session, call, due_in_seconds=3600)

        result = await tasks._dispatch_due_retries_async(session=db_session)

        assert job.id not in result["job_ids"]
        await db_session.refresh(job)
        assert job.status == JobStatus.DEFERRED
        assert not [e for e in queue.enqueued if e[1][0] == call.id]

    async def test_dispatch_does_not_duplicate_on_rerun(self, db_session, seed, queue):
        call = await seed.make_call(status=CallStatus.BUSY)
        job = await self._defer(db_session, call)

        await tasks._dispatch_due_retries_async(session=db_session)
        second = await tasks._dispatch_due_retries_async(session=db_session)

        assert job.id not in second["job_ids"]
        assert len([e for e in queue.enqueued if e[1][0] == call.id]) == 1

    async def test_ineligible_call_closes_the_job(self, db_session, seed, queue):
        call = await seed.make_call(status=CallStatus.NO_ANSWER)
        job = await self._defer(db_session, call)

        # Call succeeded between scheduling and dispatch
        call.status = CallStatus.COMPLETED
        await db_session.commit()

        result = await tasks._dispatch_due_retries_async(session=db_session)

        assert job.id not in result["job_ids"]
        await db_session.refresh(job)
        assert job.status == JobStatus.COMPLETED
        assert job.result["skipped"] is True
        assert not [e for e in queue.enqueued if e[1][0] == call.id]


class TestCampaignActivation:
    """A campaign activates once and honours its scheduled start."""

    async def test_activation_queues_one_scheduling_job(self, db_session, seed, queue):
        result = await tasks._activate_campaign_async(seed.campaign.id, session=db_session)

        assert result["status"] == "scheduled"

        jobs = await db_session.execute(
            select(Job).where(
                Job.campaign_id == seed.campaign.id,
                Job.job_type == JobType.SCHEDULE_CAMPAIGN_CALLS,
            )
        )
        jobs = list(jobs.scalars().all())
        assert len(jobs) == 1
        assert jobs[0].idempotency_key == f"campaign_activation_{seed.campaign.id}"
        assert len(queue.enqueued) == 1

    async def test_activation_is_idempotent(self, db_session, seed, queue):
        first = await tasks._activate_campaign_async(seed.campaign.id, session=db_session)
        second = await tasks._activate_campaign_async(seed.campaign.id, session=db_session)

        assert first["status"] == "scheduled"
        assert second["status"] == "skipped"
        assert second["reason"] == "already_activated"
        assert second["job_id"] == first["job_id"]
        assert len(queue.enqueued) == 1

    async def test_non_active_campaign_is_not_activated(self, db_session, seed, queue):
        seed.campaign.status = CampaignStatus.DRAFT
        await db_session.commit()

        result = await tasks._activate_campaign_async(seed.campaign.id, session=db_session)

        assert result["status"] == "skipped"
        assert result["reason"] == "campaign_not_active_draft"
        assert queue.enqueued == []

    async def test_future_start_defers_the_job(self, db_session, seed, queue):
        start = tasks._utcnow() + timedelta(hours=2)
        seed.campaign.scheduled_start = start
        await db_session.commit()

        result = await tasks._activate_campaign_async(seed.campaign.id, session=db_session)

        assert result["status"] == "deferred"
        assert queue.enqueued == []
        assert len(queue.scheduled) == 1
        assert queue.scheduled[0][3] == start.replace(tzinfo=timezone.utc)

        job = await JobService(db_session).get_by_idempotency_key(
            f"campaign_activation_{seed.campaign.id}"
        )
        assert job.status == JobStatus.DEFERRED


class TestCampaignScheduling:
    """Campaign scheduling enqueues each pending call exactly once."""

    async def _campaign_job(self, db_session, seed):
        job = await JobService(db_session).create_job(
            job_type=JobType.SCHEDULE_CAMPAIGN_CALLS,
            campaign_id=seed.campaign.id,
        )
        await db_session.commit()
        return job

    async def test_enqueues_pending_calls(self, db_session, seed, queue):
        calls = [await seed.make_call() for _ in range(3)]
        job = await self._campaign_job(db_session, seed)

        result = await tasks._schedule_campaign_calls_async(
            seed.campaign.id, job.id, session=db_session
        )

        assert result["status"] == "completed"
        assert result["calls_enqueued"] == 3
        assert len(queue.enqueued) == 3

        for call in calls:
            call_jobs = await _jobs_for_call(db_session, call.id, JobType.INITIATE_CALL)
            assert len(call_jobs) == 1
            assert call_jobs[0].idempotency_key == (
                f"campaign_call_{seed.campaign.id}_{call.id}"
            )
            assert call_jobs[0].status == JobStatus.QUEUED

        await db_session.refresh(job)
        assert job.status == JobStatus.COMPLETED

    async def test_rerun_does_not_duplicate_call_jobs(self, db_session, seed, queue):
        calls = [await seed.make_call() for _ in range(2)]
        job = await self._campaign_job(db_session, seed)

        await tasks._schedule_campaign_calls_async(
            seed.campaign.id, job.id, session=db_session
        )
        second = await tasks._schedule_campaign_calls_async(
            seed.campaign.id, job.id, session=db_session
        )

        assert second["calls_enqueued"] == 0
        assert second["calls_skipped"] == 2
        assert len(queue.enqueued) == 2

        for call in calls:
            assert len(await _jobs_for_call(db_session, call.id, JobType.INITIATE_CALL)) == 1

    async def test_future_scheduled_time_is_deferred(self, db_session, seed, queue):
        run_at = tasks._utcnow() + timedelta(hours=1)
        due_now = await seed.make_call()
        later = await seed.make_call(scheduled_time=run_at)
        job = await self._campaign_job(db_session, seed)

        result = await tasks._schedule_campaign_calls_async(
            seed.campaign.id, job.id, session=db_session
        )

        assert result["calls_enqueued"] == 1
        assert result["calls_deferred"] == 1
        assert [e[1][0] for e in queue.enqueued] == [due_now.id]
        assert [s[1][0] for s in queue.scheduled] == [later.id]
        assert queue.scheduled[0][3] == run_at.replace(tzinfo=timezone.utc)

        deferred_job = (await _jobs_for_call(db_session, later.id, JobType.INITIATE_CALL))[0]
        assert deferred_job.status == JobStatus.DEFERRED

    async def test_campaign_start_in_future_blocks_scheduling(self, db_session, seed, queue):
        await seed.make_call()
        seed.campaign.scheduled_start = tasks._utcnow() + timedelta(hours=3)
        await db_session.commit()
        job = await self._campaign_job(db_session, seed)

        result = await tasks._schedule_campaign_calls_async(
            seed.campaign.id, job.id, session=db_session
        )

        assert result["status"] == "deferred"
        assert result["reason"] == "scheduled_start_in_future"
        assert queue.enqueued == []

    async def test_paused_campaign_schedules_nothing(self, db_session, seed, queue):
        call = await seed.make_call()
        seed.campaign.status = CampaignStatus.PAUSED
        await db_session.commit()
        job = await self._campaign_job(db_session, seed)

        result = await tasks._schedule_campaign_calls_async(
            seed.campaign.id, job.id, session=db_session
        )

        assert result["status"] == "skipped"
        assert result["reason"] == "campaign_not_active_paused"
        assert queue.enqueued == []
        assert not await _jobs_for_call(db_session, call.id, JobType.INITIATE_CALL)

    async def test_non_pending_calls_are_left_alone(self, db_session, seed, queue):
        done = await seed.make_call(status=CallStatus.COMPLETED)
        job = await self._campaign_job(db_session, seed)

        result = await tasks._schedule_campaign_calls_async(
            seed.campaign.id, job.id, session=db_session
        )

        assert result["calls_enqueued"] == 0
        assert not await _jobs_for_call(db_session, done.id, JobType.INITIATE_CALL)


class TestFollowUpScheduling:
    """Follow-ups are created only where required, and only once."""

    async def _followups_for_call(self, db_session, call_id, followup_type=None):
        query = select(FollowUp).where(FollowUp.call_id == call_id)
        if followup_type is not None:
            query = query.where(FollowUp.type == followup_type)
        result = await db_session.execute(query)
        return list(result.scalars().all())

    async def _batch_job(self, db_session, seed):
        job = await JobService(db_session).create_job(
            job_type=JobType.CREATE_FOLLOWUP_CALLS
        )
        await db_session.commit()
        seed.extra_job_ids.append(job.id)
        return job

    async def test_callback_request_creates_followup(self, db_session, seed):
        call = await seed.make_call(status=CallStatus.CALLBACK_REQUESTED)
        job = await self._batch_job(db_session, seed)

        result = await tasks._create_followup_calls_async(job.id, session=db_session)

        assert result["status"] == "completed"

        followups = await self._followups_for_call(
            db_session, call.id, FollowUpType.CALLBACK_REQUESTED
        )
        assert len(followups) == 1
        assert followups[0].priority == FollowUpPriority.HIGH
        assert followups[0].status == FollowUpStatus.PENDING
        assert followups[0].due_date == tasks._utcnow().date() + timedelta(days=1)

        await db_session.refresh(job)
        assert job.status == JobStatus.COMPLETED
        assert job.completed_at is not None
        assert job.result["followups_created"] >= 1

    async def test_batch_rerun_creates_no_duplicates(self, db_session, seed):
        call = await seed.make_call(status=CallStatus.CALLBACK_REQUESTED)

        first_job = await self._batch_job(db_session, seed)
        await tasks._create_followup_calls_async(first_job.id, session=db_session)

        second_job = await self._batch_job(db_session, seed)
        await tasks._create_followup_calls_async(second_job.id, session=db_session)

        assert len(await self._followups_for_call(db_session, call.id)) == 1

    async def test_low_confidence_report_creates_followup(self, db_session, seed):
        call = await seed.make_call(status=CallStatus.COMPLETED)
        report = await seed.make_report(
            call, confidence_score=0.6, category=AbsenceCategory.OTHER
        )
        job = await self._batch_job(db_session, seed)

        await tasks._create_followup_calls_async(job.id, session=db_session)

        result = await db_session.execute(
            select(FollowUp).where(FollowUp.absence_report_id == report.id)
        )
        followups = list(result.scalars().all())
        assert len(followups) == 1
        assert followups[0].type == FollowUpType.LOW_CONFIDENCE
        assert followups[0].priority == FollowUpPriority.MEDIUM

    async def test_medical_report_uses_verification_type(self, db_session, seed):
        call = await seed.make_call(status=CallStatus.COMPLETED)
        report = await seed.make_report(
            call, confidence_score=0.7, category=AbsenceCategory.MEDICAL
        )
        job = await self._batch_job(db_session, seed)

        await tasks._create_followup_calls_async(job.id, session=db_session)

        result = await db_session.execute(
            select(FollowUp).where(FollowUp.absence_report_id == report.id)
        )
        followup = result.scalars().first()
        assert followup.type == FollowUpType.MEDICAL_VERIFICATION

    async def test_reviewed_report_needs_no_followup(self, db_session, seed):
        call = await seed.make_call(status=CallStatus.COMPLETED)
        report = await seed.make_report(
            call,
            confidence_score=0.4,
            reviewed_by=seed.user.id,
            reviewed_at=tasks._utcnow(),
        )
        job = await self._batch_job(db_session, seed)

        await tasks._create_followup_calls_async(job.id, session=db_session)

        result = await db_session.execute(
            select(FollowUp).where(FollowUp.absence_report_id == report.id)
        )
        assert result.scalars().first() is None

    async def test_report_followup_does_not_block_callback_followup(self, db_session, seed):
        call = await seed.make_call(status=CallStatus.CALLBACK_REQUESTED)
        await seed.make_report(call, confidence_score=0.6)
        job = await self._batch_job(db_session, seed)

        await tasks._create_followup_calls_async(job.id, session=db_session)

        types = {f.type for f in await self._followups_for_call(db_session, call.id)}
        assert FollowUpType.CALLBACK_REQUESTED in types
        assert FollowUpType.LOW_CONFIDENCE in types

    async def test_batch_is_not_queued_twice(self, db_session, seed, queue):
        first = await tasks._schedule_followups_async(session=db_session)
        second = await tasks._schedule_followups_async(session=db_session)

        assert first["status"] == "scheduled"
        assert second["status"] == "skipped"
        assert second["reason"] == "batch_already_pending"
        assert second["job_id"] == first["job_id"]
        assert len(queue.enqueued) == 1

        # Clean up the batch jobs (not tied to this test's call/campaign)
        await db_session.execute(delete(Job).where(Job.id == first["job_id"]))
        await db_session.commit()

"""
Tests for Phase 10 background job infrastructure.

Focus on:
- Fresh session per task
- JobType consistency
- Idempotency
- Retry eligibility
- Job lifecycle
"""
import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Call, CallStatus, Job, JobStatus, JobType, Attendance, Student, Parent
from app.services.job_service import JobService
from app.core.db_worker import run_async_task


class TestJobTypeConsistency:
    """Verify JobType enum has all required values."""

    def test_all_job_types_defined(self):
        """Ensure all job types are in enum."""
        required_types = {
            "SCHEDULE_CAMPAIGN_CALLS",
            "INITIATE_CALL",
            "RETRY_CALL",
            "CREATE_FOLLOWUP_CALLS",
            "GENERATE_REPORT",
            "PROCESS_COMPLETION"
        }

        available_types = {name for name, _ in JobType.__members__.items()}
        assert required_types == available_types, \
            f"JobType mismatch. Expected: {required_types}, Got: {available_types}"

    def test_job_type_values_are_strings(self):
        """Ensure all JobType values are strings."""
        for job_type in JobType:
            assert isinstance(job_type.value, str)


class TestJobServiceIdempotency:
    """Test Job service idempotency mechanisms."""

    @pytest.mark.asyncio
    async def test_create_job_with_idempotency_key(self, db_session: AsyncSession):
        """Test that same idempotency_key returns existing job."""
        job_service = JobService(db_session)

        # Create first job
        job1 = await job_service.create_job(
            job_type=JobType.INITIATE_CALL,
            call_id="call-123",
            idempotency_key="test_idempotency_key_1"
        )
        assert job1 is not None
        job1_id = job1.id

        # Create second job with same idempotency key
        job2 = await job_service.create_job(
            job_type=JobType.INITIATE_CALL,
            call_id="call-123",
            idempotency_key="test_idempotency_key_1"
        )

        # Should return the same job
        assert job2.id == job1_id
        assert job2.idempotency_key == "test_idempotency_key_1"

    @pytest.mark.asyncio
    async def test_create_job_without_idempotency_key(self, db_session: AsyncSession):
        """Test creating jobs without idempotency key creates new ones."""
        job_service = JobService(db_session)

        job1 = await job_service.create_job(
            job_type=JobType.INITIATE_CALL,
            call_id="call-123"
        )
        job2 = await job_service.create_job(
            job_type=JobType.INITIATE_CALL,
            call_id="call-123"
        )

        # Should be different jobs
        assert job1.id != job2.id

    @pytest.mark.asyncio
    async def test_campaign_call_idempotency_key_format(self, db_session: AsyncSession):
        """Test idempotency key format for campaign calls."""
        job_service = JobService(db_session)
        campaign_id = "campaign-123"
        call_id = "call-456"

        idempotency_key = f"campaign_call_{campaign_id}_{call_id}"

        job = await job_service.create_job(
            job_type=JobType.INITIATE_CALL,
            call_id=call_id,
            campaign_id=campaign_id,
            idempotency_key=idempotency_key
        )

        assert job.idempotency_key == idempotency_key
        assert job.call_id == call_id
        assert job.campaign_id == campaign_id


class TestJobServiceLifecycle:
    """Test Job service state transitions."""

    @pytest.mark.asyncio
    async def test_job_status_transitions(self, db_session: AsyncSession):
        """Test job lifecycle: QUEUED → STARTED → COMPLETED."""
        job_service = JobService(db_session)

        job = await job_service.create_job(
            job_type=JobType.INITIATE_CALL,
            call_id="call-123"
        )
        assert job.status == JobStatus.QUEUED
        assert job.started_at is None

        # Mark started
        success = await job_service.mark_started(job.id)
        assert success
        job = await job_service.get_job(job.id)
        assert job.status == JobStatus.STARTED
        assert job.started_at is not None

        # Mark completed
        success = await job_service.mark_completed(job.id, {"result": "success"})
        assert success
        job = await job_service.get_job(job.id)
        assert job.status == JobStatus.COMPLETED
        assert job.completed_at is not None
        assert job.duration_seconds is not None
        assert job.result == {"result": "success"}

    @pytest.mark.asyncio
    async def test_job_failure_tracking(self, db_session: AsyncSession):
        """Test job failure state and error message persistence."""
        job_service = JobService(db_session)

        job = await job_service.create_job(
            job_type=JobType.RETRY_CALL,
            call_id="call-123"
        )

        error_msg = "Provider API returned 500 error"
        success = await job_service.mark_failed(job.id, error_msg)
        assert success

        job = await job_service.get_job(job.id)
        assert job.status == JobStatus.FAILED
        assert job.error_message == error_msg
        assert job.completed_at is not None

    @pytest.mark.asyncio
    async def test_job_retry_scheduling(self, db_session: AsyncSession):
        """Test retry job creation with backoff."""
        job_service = JobService(db_session)

        original_job = await job_service.create_job(
            job_type=JobType.RETRY_CALL,
            call_id="call-123",
            max_retries=3,
            idempotency_key="original_call_job"
        )

        # Schedule first retry with 5 minute delay
        retry_job = await job_service.schedule_retry(original_job.id, delay_seconds=300)
        assert retry_job is not None
        assert retry_job.retry_count == 1
        assert retry_job.status == JobStatus.DEFERRED
        assert retry_job.next_retry_at is not None
        assert "retry_1" in retry_job.idempotency_key

    @pytest.mark.asyncio
    async def test_max_retries_enforcement(self, db_session: AsyncSession):
        """Test that scheduling fails when max retries exceeded."""
        job_service = JobService(db_session)

        job = await job_service.create_job(
            job_type=JobType.RETRY_CALL,
            call_id="call-123",
            max_retries=1
        )

        # First retry
        retry1 = await job_service.schedule_retry(job.id, delay_seconds=300)
        assert retry1 is not None
        assert retry1.retry_count == 1

        # Second retry should fail (exceeds max_retries=1)
        retry2 = await job_service.schedule_retry(retry1.id, delay_seconds=300)
        assert retry2 is None

        # retry1 should be marked failed (not original job)
        retry1_updated = await job_service.get_job(retry1.id)
        assert retry1_updated.status == JobStatus.FAILED


class TestAsyncTaskBridge:
    """Test async task execution from sync RQ context."""

    def test_run_async_task_executes_coroutine(self):
        """Test that run_async_task executes async function."""
        async def sample_async_task():
            return {"result": "success"}

        result = run_async_task(sample_async_task())
        assert result == {"result": "success"}

    def test_run_async_task_propagates_exceptions(self):
        """Test that exceptions are propagated."""
        async def failing_task():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            run_async_task(failing_task())


class TestJobTypeUsage:
    """Test JobType consistency across services."""

    @pytest.mark.asyncio
    async def test_job_type_enum_in_create_job(self, db_session: AsyncSession):
        """Test that create_job accepts JobType enum values."""
        job_service = JobService(db_session)

        for job_type in [
            JobType.INITIATE_CALL,
            JobType.RETRY_CALL,
            JobType.SCHEDULE_CAMPAIGN_CALLS
        ]:
            job = await job_service.create_job(
                job_type=job_type,
                call_id="call-123"
            )
            assert job.job_type == job_type


class TestImportStructure:
    """Test that imports work correctly without cycles."""

    def test_import_tasks_module(self):
        """Verify tasks module can be imported."""
        from app import tasks
        assert hasattr(tasks, 'initiate_pending_call')
        assert hasattr(tasks, 'retry_failed_call')
        assert hasattr(tasks, 'schedule_campaign_calls')

    def test_import_job_service(self):
        """Verify job_service module can be imported."""
        from app.services.job_service import JobService
        assert JobService is not None

    def test_import_rq_config(self):
        """Verify rq_config module can be imported."""
        from app.core.rq_config import get_call_queue, RQHealthCheck
        assert get_call_queue is not None
        assert RQHealthCheck is not None
